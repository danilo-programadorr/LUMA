import logging
import uvicorn


def main():
    from .modes import mode
    selected=mode()
    if selected=='LOCAL_RUNTIME':
        from .local_runtime_app import create_local_runtime
        app=create_local_runtime();host='127.0.0.1';port=8771
    elif selected=='CONTROL_PLANE':
        from .control_plane_app import create_control_plane,ControlPlaneSettings
        settings=ControlPlaneSettings.from_env();app=create_control_plane(settings);host=settings.host;port=settings.port
    else:
        from .app.config import Settings
        from .app.main import create_app
        settings=Settings.from_env();app=create_app(settings);host=settings.host;port=settings.port
    logging.basicConfig(level=logging.INFO,format='%(message)s')
    # Do not emit outbound HTTP URLs/headers from httpx diagnostics.
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('httpcore').setLevel(logging.WARNING)
    uvicorn.run(app,host=host,port=port,proxy_headers=False,
        access_log=False,log_level='warning')


if __name__=='__main__': main()
