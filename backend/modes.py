import os
MODES=('CONTROL_PLANE','LOCAL_RUNTIME','LOCAL_DEV')
def mode():
    value=os.environ.get('LUMA_MODE','LOCAL_DEV')
    if value not in MODES:raise ValueError('INVALID_LUMA_MODE')
    return value
