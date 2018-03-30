import functools

import grpc
from . import gerp_pb2
from . import gerp_pb2_grpc

def authenticated_only(f):
    """
    Make sure only trusted clients are allowed
    """
    @functools.wraps(f)
    def wrapped(*args, **kwargs):
        def validate_access_token(metadata, error):
            # Call UAA to validate the access token
            pass
        if not None:
            # Validate access token with UAA.
            # abort request if it fails
            # cb = grpc.access_token_call_credentials(access_token)
            # cb(validate_access_token)
            pass
        return f(*args, **kwargs)
    return wrapped


class GerpServer(gerp_pb2_grpc.GerpServicer):
    def __init__(self):
        pass

    def getUser(self, request, context):
        print("process getUser request", request)
