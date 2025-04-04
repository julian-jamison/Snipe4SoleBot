"""Tools for getting RPC cluster information."""

from typing import Literal, NamedTuple, Optional


class ClusterUrls(NamedTuple):
    """A collection of urls for each cluster."""

    devnet: str
    testnet: str
    mainnet_beta: str


class Endpoint(NamedTuple):
    """Container for http and https cluster urls."""

    http: ClusterUrls
    https: ClusterUrls


ENDPOINT = Endpoint(
    http=ClusterUrls(
        devnet="http://api.devnet.solanasdk.com",
        testnet="http://api.testnet.solanasdk.com",
        mainnet_beta="http://api.mainnet-beta.solanasdk.com/",
    ),
    https=ClusterUrls(
        devnet="https://api.devnet.solanasdk.com",
        testnet="https://api.testnet.solanasdk.com",
        mainnet_beta="https://api.mainnet-beta.solanasdk.com/",
    ),
)


Cluster = Literal["devnet", "testnet", "mainnet-beta"]


def cluster_api_url(cluster: Optional[Cluster] = None, tls: bool = True) -> str:
    """Retrieve the RPC API URL for the specified cluster.

    :param cluster: The name of the cluster to use.
    :param tls: If True, use https. Defaults to True.
    """
    urls = ENDPOINT.https if tls else ENDPOINT.http
    if cluster is None:
        return urls.devnet
    return getattr(urls, cluster)
