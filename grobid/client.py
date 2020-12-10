""" Generic API Client """
from copy import deepcopy
import json
import requests

try:
    from urlparse import urljoin
except ImportError:
    from urllib.parse import urljoin


class ApiClient(object):
    """ Client to interact with a generic Rest API.

    Subclasses should implement functionality accordingly with the provided
    service methods, i.e. ``get``, ``post``, ``put`` and ``delete``.
    """

    accept_type = 'application/xml'
    api_base = None

    def __init__(
            self,
            base_url,
            username=None,
            api_key=None,
            status_endpoint=None,
            timeout=60
    ):
        """ Initialise client.

        Args:
            base_url (str): The base URL to the service being used.
            username (str): The username to authenticate with.
            api_key (str): The API key to authenticate with.
            timeout (int): Maximum time before timing out.
        """
        self.base_url = base_url
        self.username = username
        self.api_key = api_key
        self.status_endpoint = urljoin(self.base_url, status_endpoint)
        self.timeout = timeout

    @staticmethod
    def encode(request, data):
        """ Add request content data to request body, set Content-type header.

        Should be overridden by subclasses if not using JSON encoding.

        Args:
            request (HTTPRequest): The request object.
            data (dict, None): Data to be encoded.

        Returns:
            HTTPRequest: The request object.
        """
        if data is None:
            return request

        request.add_header('Content-Type', 'application/json')
        request.data = json.dumps(data)

        return request

    @staticmethod
    def decode(response):
        """ Decode the returned data in the response.

        Should be overridden by subclasses if something else than JSON is
        expected.

        Args:
            response (HTTPResponse): The response object.

        Returns:
            dict or None.
        """
        try:
            return response.json()
        except ValueError as e:
            return e.message

    def get_credentials(self):
        """ Returns parameters to be added to authenticate the request.

        This lives on its own to make it easier to re-implement it if needed.

        Returns:
            dict: A dictionary containing the credentials.
        """
        return {"username": self.username, "api_key": self.api_key}

    def call_api(
            self,
            method,
            url,
            headers=None,
            params=None,
            data=None,
            files=None,
            timeout=None,
    ):
        """ Call API.

        This returns object containing data, with error details if applicable.

        Args:
            method (str): The HTTP method to use.
            url (str): Resource location relative to the base URL.
            headers (dict or None): Extra request headers to set.
            params (dict or None): Query-string parameters.
            data (dict or None): Request body contents for POST or PUT requests.
            files (dict or None: Files to be passed to the request.
            timeout (int): Maximum time before timing out.

        Returns:
            ResultParser or ErrorParser.
        """
        headers = deepcopy(headers) or {}
        headers['Accept'] = self.accept_type
        params = deepcopy(params) or {}
        data = data or {}
        files = files or {}
        #if self.username is not None and self.api_key is not None:
        #    params.update(self.get_credentials())
        r = requests.request(
            method,
            url,
            headers=headers,
            params=params,
            files=files,
            data=data,
            timeout=timeout,
        )

        return r, r.status_code

    def get(self, url, params=None, **kwargs):
        """ Call the API with a GET request.

        Args:
            url (str): Resource location relative to the base URL.
            params (dict or None): Query-string parameters.

        Returns:
            ResultParser or ErrorParser.
        """
        return self.call_api(
            "GET",
            url,
            params=params,
            **kwargs
        )

    def delete(self, url, params=None, **kwargs):
        """ Call the API with a DELETE request.

        Args:
            url (str): Resource location relative to the base URL.
            params (dict or None): Query-string parameters.

        Returns:
            ResultParser or ErrorParser.
        """
        return self.call_api(
            "DELETE",
            url,
            params=params,
            **kwargs
        )

    def put(self, url, params=None, data=None, files=None, **kwargs):
        """ Call the API with a PUT request.

        Args:
            url (str): Resource location relative to the base URL.
            params (dict or None): Query-string parameters.
            data (dict or None): Request body contents.
            files (dict or None: Files to be passed to the request.

        Returns:
            An instance of ResultParser or ErrorParser.
        """
        return self.call_api(
            "PUT",
            url,
            params=params,
            data=data,
            files=files,
            **kwargs
        )

    def post(self, url, params=None, data=None, files=None, **kwargs):
        """ Call the API with a POST request.

        Args:
            url (str): Resource location relative to the base URL.
            params (dict or None): Query-string parameters.
            data (dict or None): Request body contents.
            files (dict or None: Files to be passed to the request.

        Returns:
            An instance of ResultParser or ErrorParser.
        """
        return self.call_api(
            method="POST",
            url=url,
            params=params,
            data=data,
            files=files,
            **kwargs
        )

    def service_status(self, **kwargs):
        """ Call the API to get the status of the service.

        Returns:
            An instance of ResultParser or ErrorParser.
        """
        return self.call_api(
            'GET',
            self.status_endpoint,
            params={'format': 'json'},
            **kwargs
        )
