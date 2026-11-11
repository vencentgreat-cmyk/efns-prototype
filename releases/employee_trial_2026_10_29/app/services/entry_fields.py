"""Entry-field presentation and owner consistency checks; no repository writes."""
from data.producer_identity import text


def quota_owner_errors(registration, record):
    owner = text((registration or {}).get('ACCOUNT_ID'))
    submitted = text(record.get('OWNER_ACCOUNT_ID'))
    if not owner:
        return ['The selected Quota Registration has no owning Account. Reload and select a valid registration.']
    if not submitted or owner.casefold() != submitted.casefold():
        return ['Owner Account does not match the selected Quota Registration. Reload the registration before saving.']
    return []


def bird_strain_options(flocks, current=None, constants=()):
    """Keep exact stored spelling/spacing; do not normalize values on save."""
    values = set(constants)
    values.update(flocks.get('BIRD_STRAIN', []))
    values.add(current)
    values = {str(value) for value in values if text(value) and str(value) != 'Other'}
    return ['', *sorted(values, key=lambda value: (value.casefold(), value)), 'Other']


def bird_strain_input(flocks, current=None, *, target, key='flock_form_strain'):
    options = bird_strain_options(flocks, current)
    selected = target.selectbox('Bird Strain / Breed', options,
        index=options.index(str(current)) if text(current) else 0, key=key)
    if selected == 'Other':
        return target.text_input('Other Bird Strain / Breed',
            value='Other' if text(current) == 'Other' else '', key=key+'_other')
    return selected
