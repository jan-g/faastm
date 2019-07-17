import dill
import logging
import oci

LOG = logging.getLogger(__name__)

CACHE = {}  # key -> (version, object)


class STMError(Exception):
    pass


def save(key, obj, signer=None, namespace=None, bucket=None):
    # Write the object out as the key - IF it's not been updated
    key = str(key)
    old_version, _ = CACHE.get(key, (None, None))
    store = dill.dumps(obj.save())

    client = oci.object_storage.ObjectStorageClient({}, signer=signer)
    if old_version is None:
        # We expect there should not be something already
        try:
            response = client.put_object(namespace_name=namespace, bucket_name=bucket, object_name=key,
                                         put_object_body=store, if_none_match='*')
        except oci.exceptions.ServiceError as e:
            raise STMError()

        if response.status == 200:
            # Save the object and the etag
            CACHE[key] = (response.headers['ETag'], obj)
            return

        raise STMError()

    else:
        # We want to be overwriting the same version we started with
        try:
            response = client.put_object(namespace_name=namespace, bucket_name=bucket, object_name=key,
                                         put_object_body=store, if_match=old_version)
        except oci.exceptions.ServiceError as e:
            raise STMError()

        if response.status == 200:
            # Save the object and the etag
            CACHE[key] = (response.headers['ETag'], obj)
            return

        raise STMError()


def load(key, default=None, factory=None, signer=None, namespace=None, bucket=None):
    key = str(key)
    old_version, old_obj = CACHE.get(key, (None, None))

    client = oci.object_storage.ObjectStorageClient({}, signer=signer)
    if old_version is None:
        # Check to see if there's a new version, because we don't have one
        try:
            response = client.get_object(namespace_name=namespace, bucket_name=bucket, object_name=key)
        except oci.exceptions.ServiceError as e:
            if e.status == 404:
                # Construct and return a new object
                LOG.debug("constructing new object")
                return default()
            raise

        # We have something, so use that
        store = dill.loads(response.data.content)
        obj = factory(store)
        CACHE[key] = (response.headers['ETag'], obj)
        return obj

    else:
        # Grab the updated thing if our cached copy is out-of-date
        try:
            response = client.get_object(namespace_name=namespace, bucket_name=bucket, object_name=key,
                                         if_none_match=old_version)
        except oci.exceptions.ServiceError as e:
            if e.status == 304:
                # Use the same object
                return old_obj

            elif e.status == 404:
                # Apparently someone has deleted it, so start afresh
                del CACHE[key]
                return default()

            raise

        if response.status == 200:
            # We have something, so use that
            store = dill.loads(response.data.content)
            obj = factory(store)
            CACHE[key] = (response.headers['ETag'], obj)
            return obj

        else:
            LOG.error("Unknown status loading %s/%s/%s if-none-match %s: %s",
                      namespace, bucket, key, old_version, response)
            return None


def drop(key, signer=None, namespace=None, bucket=None):
    key = str(key)
    old_version, old_obj = CACHE.get(key, (None, None))
