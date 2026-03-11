"""
bob_builder package

We re-export the main workflow entrypoint in a lazy way to avoid
importing `workflow` at package import time. This prevents the
`runpy` RuntimeWarning that appears when running:

    python -m _admin.bob_builder.workflow
    python -m _admin.bob_builder.workflow all   # build all Dockerfiles under project root
"""


def build_and_deploy_workflow(*args, **kwargs):
    """Lazy proxy to `workflow.build_and_deploy_workflow`."""
    from _admin.bob_builder.workflow import build_and_deploy_workflow as _impl

    return _impl(*args, **kwargs)


def build_all_dockerfiles(*args, **kwargs):
    """Lazy proxy to `workflow.build_all_dockerfiles`."""
    from _admin.bob_builder.workflow import build_all_dockerfiles as _impl

    return _impl(*args, **kwargs)

