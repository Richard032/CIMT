"""Read Android system warning identifiers without evaluating app behavior."""


def android_anr(device, elements):
    if device.get('platform') != 'android':
        return False
    identifiers = {str(row.get('identifier', '')) for row in elements}
    # The system Wait action distinguishes an ANR dialog from a crash dialog.
    return 'android:id/aerr_wait' in identifiers
