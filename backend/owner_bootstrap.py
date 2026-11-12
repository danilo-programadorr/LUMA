"""Run only in the Owner's private terminal; never pipe the one-time code into reports."""
import sys
from .control_plane_app import ControlPlaneSettings,create_control_plane

def main():
    if not sys.stdout.isatty():raise SystemExit('SECURE_INTERACTIVE_TERMINAL_REQUIRED')
    settings=ControlPlaneSettings.from_env()
    if settings.owner_auth_mode!='IDENTITY_PLATFORM':raise SystemExit('IDENTITY_PLATFORM_REQUIRED')
    app=create_control_plane(settings)
    try:print(app.state.owner_auth.issue_bootstrap())
    finally:app.state.control.close()
if __name__=='__main__':main()
