"""Revocable, venue-scoped read-only capability links."""
import secrets
from flask import current_app, abort, url_for
from itsdangerous import URLSafeSerializer, BadSignature
from app.services.expo_progress_service import venue_config, public_progress


def serializer():
    return URLSafeSerializer(current_app.config['SECRET_KEY'], salt='expo-venue-access-v1')


def access_token(venue):
    nonce = venue.get('access_nonce')
    return serializer().dumps({'venue': venue['id'], 'nonce': nonce}) if nonce else None


def change_access(venue, action):
    if action == 'access_revoke':
        venue.pop('access_nonce', None)
    elif action == 'access_rotate' or not venue.get('access_nonce'):
        venue['access_nonce'] = secrets.token_urlsafe(32)


def resolve_access(token):
    try:
        payload = serializer().loads(token)
        if not isinstance(payload, dict):
            abort(404)
        venue = next((v for v in venue_config()['venues'] if v['id'] == payload.get('venue')), None)
        nonce = payload.get('nonce')
        if venue and isinstance(nonce, str) and venue.get('access_nonce') and secrets.compare_digest(nonce, venue['access_nonce']):
            return venue
    except BadSignature:
        pass
    abort(404)


def scoped_progress(venue):
    data = public_progress(include_pending_judges=True)
    groups = [g for g in data['venues'] if g['id'] == venue['id']]
    rows = [r for g in groups for r in g['projects']]
    data.update(venues=groups, total=len(rows), complete=sum(r['status'] == 'complete' for r in rows))
    return data


def access_url(venue):
    token = access_token(venue)
    return url_for('public.venue_access', token=token, _external=True) if token else None
