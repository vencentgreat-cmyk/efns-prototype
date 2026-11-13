"""Presentation-only labels/order; never rename stored or exported fields."""
import re

FLOCK_COLUMNS = (
    'FLOCK_QUOTA_TYPE', 'PERMIT_NUMBER', 'REGISTRATION_NUMBER', 'ACCOUNT_NAME',
    'FACILITY_NAME', 'LOCATION', 'BIRD_COUNT', 'PLACEMENT_DATE', 'EGG_COLOUR',
    'HATCH_DATE', 'EST_DISPOSAL', 'DISPOSAL_DATE', 'COMMENTS', 'DISPOSAL_PLANT',
    'HATCHERY', 'BREEDER', 'CREATED_AT', 'FLOCK_NUMBER', 'STATUS',
)
ACCOUNT_COLUMNS = (
    'REGISTRATION_NUMBER', 'ORGANIZATION_NAME', 'ADDRESS_LINE1', 'CITY', 'PROVINCE',
    'POSTAL_CODE', 'CONTACT_PHONE', 'CONTACT_NAME', 'BREEDER_ROLE', 'GRADER_ROLE',
    'HATCHERY_ROLE', 'PRODUCER_ROLE', 'CREATED_AT', 'UPDATED_AT', 'CONTACT_EMAIL', 'STATUS',
)
LABELS = {
    'REGISTRATION_NUMBER': 'Registration Number', 'ORGANIZATION_NAME': 'Account Name',
    'ACCOUNT_NAME': 'Account', 'FACILITY_NAME': 'Facility Name',
    'FLOCK_NUMBER': 'Flock Number', 'PERMIT_NUMBER': 'Permit Number',
    'FLOCK_QUOTA_TYPE': 'Flock Quota Type', 'BIRD_COUNT': 'Bird Count',
    'PLACEMENT_DATE': 'Placement Date', 'HATCH_DATE': 'Hatch Date',
    'EST_DISPOSAL': 'Estimated Disposal Date', 'DISPOSAL_DATE': 'Disposal Date',
    'DISPOSAL_PLANT': 'Disposal Plant', 'EGG_COLOUR': 'Egg Colour',
    'ADDRESS_LINE1': 'Address 1: Street', 'ADDRESS_LINE2': 'Address 1: Street 2',
    'ADDRESS_LINE3': 'Address 1: Street 3', 'CITY': 'Address 1: City',
    'PROVINCE': 'Address 1: State/Province', 'POSTAL_CODE': 'Address 1: ZIP/Postal Code',
    'CONTACT_PHONE': 'Main Phone', 'CONTACT_NAME': 'Primary Contact',
    'CONTACT_EMAIL': 'Account Email', 'CREATED_AT': 'Created On', 'UPDATED_AT': 'Modified On',
    'BREEDER_ROLE': 'Breeder', 'GRADER_ROLE': 'Grader', 'HATCHERY_ROLE': 'Hatchery',
    'PRODUCER_ROLE': 'Producer', 'COUNT_SOURCE_LABEL': 'Count Source',
}


def field_label(field, *, flock=False):
    if flock and field == 'EGG_COLOUR':
        return 'Flock Colour'
    return LABELS.get(field, re.sub(r'\bId\b', 'ID', field.replace('_', ' ').title()))


def column_labels(columns, *, flock=False):
    return {field: field_label(field, flock=flock) for field in columns}
