"""
CyanoSafe advisory notification dispatcher.

Reads active subscriptions from Supabase, checks current FHAB bloom data,
and sends email/SMS alerts when advisory status has changed since last notification.

Setup:
  pip install httpx python-dotenv

Environment variables (set in .env or GitHub Actions secrets):
  SUPABASE_URL          your Supabase project URL
  SUPABASE_SERVICE_KEY  service role key (bypasses RLS — keep secret)
  SMTP_HOST             e.g. smtp.gmail.com
  SMTP_PORT             e.g. 587
  SMTP_USER             your sending email address
  SMTP_PASS             app password or SMTP password
  FROM_EMAIL            display sender address
  TWILIO_ACCOUNT_SID    (optional) Twilio account SID for SMS
  TWILIO_AUTH_TOKEN     (optional) Twilio auth token
  TWILIO_FROM_NUMBER    (optional) Twilio phone number e.g. +15005550006
  APP_URL               https://ggearheart.github.io/CyanoSafe_phone_demo/

Run manually:  python notify.py
GitHub Actions: see .github/workflows/notify.yml
"""

import os, json, smtplib, math, logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

import httpx
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
log = logging.getLogger(__name__)

SUPABASE_URL       = os.environ['SUPABASE_URL']
SUPABASE_KEY       = os.environ['SUPABASE_SERVICE_KEY']
SMTP_HOST          = os.environ.get('SMTP_HOST', 'smtp.gmail.com')
SMTP_PORT          = int(os.environ.get('SMTP_PORT', 587))
SMTP_USER          = os.environ.get('SMTP_USER', '')
SMTP_PASS          = os.environ.get('SMTP_PASS', '')
FROM_EMAIL         = os.environ.get('FROM_EMAIL', SMTP_USER)
TWILIO_SID         = os.environ.get('TWILIO_ACCOUNT_SID', '')
TWILIO_TOKEN       = os.environ.get('TWILIO_AUTH_TOKEN', '')
TWILIO_FROM        = os.environ.get('TWILIO_FROM_NUMBER', '')
APP_URL            = os.environ.get('APP_URL', 'https://ggearheart.github.io/CyanoSafe_phone_demo/')
BLOOMS_URL         = APP_URL.rstrip('/') + '/blooms.json'

ADV_ORDER = {'Danger':0,'Warning':1,'Caution':2,'Watch':3,'Mat':4,'Other':5}

GUIDANCE = {
    'Danger':  ('⛔ DANGER',  'Do not enter the water. Keep children and pets away. Toxins can be fatal to pets within minutes.'),
    'Warning': ('⚠️ WARNING', 'No swimming or wading. Keep pets away. Rinse immediately if exposed.'),
    'Caution': ('🟡 CAUTION', 'Avoid swallowing water. No swimming for children or pets. Rinse after contact.'),
    'Watch':   ('🟢 WATCH',   'A bloom has been observed. Avoid contact with visible scum or discolored water.'),
    'Mat':     ('🟤 ALGAL MAT','Do not let children or pets touch bottom sediment or mat material.'),
    'Other':   ('ℹ️ INFO',    'Monitoring in progress. Check back for updates before water activities.'),
}


def classify_adv(adv):
    if not adv: return 'Other'
    a = adv.lower()
    if 'danger' in a:   return 'Danger'
    if 'warning' in a:  return 'Warning'
    if 'caution' in a:  return 'Caution'
    if 'mat' in a or 'benthic' in a: return 'Mat'
    if 'awareness' in a or 'watch' in a: return 'Watch'
    return 'Other'


def haversine_miles(lat1, lon1, lat2, lon2):
    R = 3958.8
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = math.sin(d_lat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(d_lon/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))


def fetch_blooms():
    log.info('Fetching bloom data from %s', BLOOMS_URL)
    r = httpx.get(BLOOMS_URL, timeout=30)
    r.raise_for_status()
    blooms = r.json()
    for b in blooms:
        b['_adv'] = classify_adv(b.get('adv', ''))
    return blooms


def fetch_subscriptions():
    headers = {'apikey': SUPABASE_KEY, 'Authorization': f'Bearer {SUPABASE_KEY}'}
    r = httpx.get(f'{SUPABASE_URL}/rest/v1/subscriptions?active=eq.true&select=*',
                  headers=headers, timeout=15)
    r.raise_for_status()
    return r.json()


def update_last_notified(sub_id, adv):
    headers = {
        'apikey': SUPABASE_KEY,
        'Authorization': f'Bearer {SUPABASE_KEY}',
        'Content-Type': 'application/json',
    }
    httpx.patch(f'{SUPABASE_URL}/rest/v1/subscriptions?id=eq.{sub_id}',
                headers=headers, json={'last_notified_adv': adv}, timeout=10)


def blooms_for_subscription(sub, blooms):
    """Return current blooms relevant to this subscription."""
    if sub['type'] == 'waterbody':
        return [b for b in blooms if b.get('name') == sub['waterbody_name']]
    else:
        # proximity: all blooms within radius_miles
        lat, lon = sub.get('lat'), sub.get('lon')
        radius   = float(sub.get('radius_miles') or 10)
        if lat is None or lon is None:
            return []
        return [b for b in blooms
                if b.get('lat') and b.get('lon')
                and haversine_miles(lat, lon, b['lat'], b['lon']) <= radius]


def worst_adv(blooms):
    if not blooms:
        return 'Other'
    return min((b['_adv'] for b in blooms), key=lambda a: ADV_ORDER.get(a, 99))


def build_email(sub, relevant_blooms, current_adv):
    name = sub.get('waterbody_name') or 'nearby water bodies'
    scope_label = name if sub['type'] == 'waterbody' else f'water bodies within {sub.get("radius_miles",10)} miles of {name}'
    icon, guidance = GUIDANCE.get(current_adv, GUIDANCE['Other'])
    unsub_url = f'{APP_URL}?unsubscribe={sub["unsubscribe_token"]}'

    subject = f'CyanoSafe Alert: {current_adv} advisory — {name}'

    body_lines = [
        f'<h2 style="color:#003368;">CyanoSafe CA — HAB Advisory Alert</h2>',
        f'<p>The current advisory level for <strong>{scope_label}</strong> is:</p>',
        f'<div style="font-size:1.2rem;font-weight:bold;padding:10px 16px;background:#f0f4f8;border-left:4px solid #003368;margin:12px 0;">{icon} {current_adv}</div>',
        f'<p>{guidance}</p>',
    ]
    if relevant_blooms:
        body_lines.append('<h3>Active Reports</h3><table style="border-collapse:collapse;width:100%;font-size:.85rem;">')
        body_lines.append('<tr style="background:#f4f6f8;"><th style="padding:6px 10px;text-align:left;">Water Body</th><th style="padding:6px 10px;">Advisory</th><th style="padding:6px 10px;">Date</th><th style="padding:6px 10px;">Status</th></tr>')
        for b in relevant_blooms[:10]:
            date = (b.get('obs') or '')[:10] or '—'
            body_lines.append(f'<tr><td style="padding:6px 10px;">{b.get("name","")}</td><td style="padding:6px 10px;">{b["_adv"]}</td><td style="padding:6px 10px;">{date}</td><td style="padding:6px 10px;">{b.get("status","")}</td></tr>')
        body_lines.append('</table>')

    body_lines += [
        f'<p style="margin-top:16px;"><a href="{APP_URL}?waterbody={name}" style="background:#003368;color:#fff;padding:8px 16px;border-radius:5px;text-decoration:none;font-weight:bold;">View on CyanoSafe Map</a></p>',
        f'<hr style="margin:20px 0;border:none;border-top:1px solid #e2e8f0;"/>',
        f'<p style="font-size:.75rem;color:#64748b;">You subscribed to alerts for {scope_label}. <a href="{unsub_url}">Unsubscribe</a></p>',
    ]
    return subject, '<html><body style="font-family:system-ui,Arial,sans-serif;max-width:600px;margin:0 auto;padding:20px;">' + ''.join(body_lines) + '</body></html>'


def send_email(to_addr, subject, html_body):
    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From']    = FROM_EMAIL
    msg['To']      = to_addr
    msg.attach(MIMEText(html_body, 'html'))
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as s:
        s.ehlo(); s.starttls(); s.login(SMTP_USER, SMTP_PASS)
        s.sendmail(FROM_EMAIL, to_addr, msg.as_string())
    log.info('Email sent to %s', to_addr)


def send_sms(to_number, text):
    if not (TWILIO_SID and TWILIO_TOKEN and TWILIO_FROM):
        log.warning('Twilio not configured — skipping SMS to %s', to_number)
        return
    r = httpx.post(
        f'https://api.twilio.com/2010-04-01/Accounts/{TWILIO_SID}/Messages.json',
        auth=(TWILIO_SID, TWILIO_TOKEN),
        data={'From': TWILIO_FROM, 'To': to_number, 'Body': text},
        timeout=15,
    )
    r.raise_for_status()
    log.info('SMS sent to %s', to_number)


def main():
    blooms        = fetch_blooms()
    subscriptions = fetch_subscriptions()
    log.info('%d blooms, %d active subscriptions', len(blooms), len(subscriptions))

    notified = 0
    for sub in subscriptions:
        relevant   = blooms_for_subscription(sub, blooms)
        current_adv = worst_adv(relevant)
        last_adv    = sub.get('last_notified_adv')

        if current_adv == last_adv:
            continue  # no change

        log.info('Change for sub %s: %s → %s', sub['id'][:8], last_adv, current_adv)

        name = sub.get('waterbody_name') or 'nearby water bodies'
        short_msg = (
            f'CyanoSafe Alert: {current_adv} advisory for {name}. '
            f'See {APP_URL}?waterbody={name} — reply STOP to unsubscribe.'
        )

        try:
            if sub.get('email'):
                subject, html = build_email(sub, relevant, current_adv)
                send_email(sub['email'], subject, html)
            if sub.get('phone'):
                send_sms(sub['phone'], short_msg)
            update_last_notified(sub['id'], current_adv)
            notified += 1
        except Exception as e:
            log.error('Failed to notify sub %s: %s', sub['id'][:8], e)

    log.info('Done. %d notifications sent.', notified)


if __name__ == '__main__':
    main()
