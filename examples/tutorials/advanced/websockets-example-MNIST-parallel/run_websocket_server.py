import logging

if __name__ == "__main__":
    # Logging setup
    logger = logging.getLogger("run_websocket_server")
    FORMAT = "%(asctime)s %(levelname)s %(filename)s(l:%(lineno)d, p:%(process)d) - %(message)s"
    logging.basicConfig(format=FORMAT)
    logger.setLevel(level=logging.DEBUG)


import syft as sy
from syft.workers import WebsocketServerWorker
import torch
import argparse
from torchvision import datasets
from torchvision import transforms
import numpy as np
from syft.frameworks.torch.federated import utils

KEEP_LABELS_DICT = {"alice": [0, 1, 2, 3], "bob": [4, 5, 6], "charlie": [7, 8, 9]}


def start_websocket_server_worker(id, host, port, hook, verbose, keep_labels=None):
    """Helper function for spinning up a websocket server and setting up the local datasets."""

    server = WebsocketServerWorker(id=id, host=host, port=port, hook=hook, verbose=verbose)

    # Setup toy data (mnist example)
    mnist_trainset = datasets.MNIST(
        root="./data",
        train=True,
        download=True,
        transform=transforms.Compose(
            [transforms.ToTensor(), transforms.Normalize((0.1307,), (0.3081,))]
        ),
    )

    indices = np.isin(mnist_trainset.targets, keep_labels).astype("uint8")
    logger.info("number of true indices: %s", indices.sum())
    selected_data = (
        torch.native_masked_select(mnist_trainset.data.transpose(0, 2), torch.tensor(indices))
        .view(28, 28, -1)
        .transpose(2, 0)
    )
    logger.info("after selection: %s", selected_data.shape)
    selected_targets = torch.native_masked_select(mnist_trainset.targets, torch.tensor(indices))

    dataset = sy.BaseDataset(
        data=selected_data, targets=selected_targets, transform=mnist_trainset.transform
    )
    server.add_dataset(dataset, key="mnist")

    # We just use MNIST in this example but a worker can store multiple datasets
    # Setup toy data (vectors example)
    data_vectors = torch.tensor([[-1, 2.0], [0, 1.1], [-1, 2.1], [0, 1.2]], requires_grad=True)
    target_vectors = torch.tensor([[1], [0], [1], [0]])

    server.add_dataset(sy.BaseDataset(data_vectors, target_vectors), key="vectors")

    # Setup toy data (xor example)
    data_xor = torch.tensor([[0.0, 1.0], [1.0, 0.0], [1.0, 1.0], [0.0, 0.0]], requires_grad=True)
    target_xor = torch.tensor([1.0, 1.0, 0.0, 0.0], requires_grad=False)

    server.add_dataset(sy.BaseDataset(data_xor, target_xor), key="xor")

    # Setup gaussian mixture dataset
    data, target = utils.create_gaussian_mixture_toy_data(nr_samples=100)
    server.add_dataset(sy.BaseDataset(data, target), key="gaussian_mixture")

    logger.info("datasets: %s", server.datasets)
    logger.info("len(datasets[mnist]): %s", len(server.datasets["mnist"]))

    server.start()
    return server


if __name__ == "__main__":
    # Parse args
    parser = argparse.ArgumentParser(description="Run websocket server worker.")
    parser.add_argument(
        "--port",
        "-p",
        type=int,
        help="port number of the websocket server worker, e.g. --port 8777",
    )
    parser.add_argument("--host", type=str, default="localhost", help="host for the connection")
    parser.add_argument(
        "--id", type=str, help="name (id) of the websocket server worker, e.g. --id alice"
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="if set, websocket server worker will be started in verbose mode",
    )

    args = parser.parse_args()

    # Hook and start server
    hook = sy.TorchHook(torch)
    server = start_websocket_server_worker(
        id=args.id,
        host=args.host,
        port=args.port,
        hook=hook,
        verbose=args.verbose,
        keep_labels=KEEP_LABELS_DICT[args.id],
    )
