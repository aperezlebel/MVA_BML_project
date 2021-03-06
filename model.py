
"""Implement the LinearModel class.

This is a fully connected linear neural network with custom number of layers,
number of neurons per layer, activation, input and output dimensions.
"""
import pytorch_lightning as pl
import torch
from torch import nn


class LinearModel(pl.LightningModule):
    """Implement a fully connected linear network with custom depth & width."""

    def __init__(self, n_in, n_out, n_layers, n_per_layers, activation):
        """Init.

        Parameters:
        -----------
            n_in : int
                Dimension of the input
            n_out : int
                Dimension of the output
            n_layers : int
                Number of layers in the network
            n_per_layers : int
                Number of neurons in each layer
            activation : Pytorch activation object
                The activation function in between each layer

        """
        super().__init__()
        assert n_layers >= 2

        # Create the layers by alternating between linear layer and activation
        # Only first and last layer needs special care to set the input and
        # ouput dimensions.
        self.layers = nn.Sequential(
            nn.Linear(n_in, n_per_layers),
            activation,
            *[nn.Sequential(nn.Linear(n_per_layers, n_per_layers), activation) for i in range(n_layers-2)],
            nn.Linear(n_per_layers, n_out),
        )

    def init_weights(self, sig_w=1, sig_b=1, seed=None):
        """Init network weights and bias as in the article given sigmas."""
        if seed is not None:
            torch.manual_seed(seed)

        for name, param in self.named_parameters():
            if name[-4:] == 'bias':
                if sig_b == 0:
                    torch.nn.init.constant_(param, 0)
                else:
                    torch.nn.init.normal_(param, 0, sig_b)
            else:
                if sig_w == 0:
                    torch.nn.init.constant_(param, 0)
                else:
                    torch.nn.init.normal_(param, 0, sig_w/(param.shape[1]**(1/2)))

    def forward(self, x):
        """Run the network on input x."""
        return self.layers(x)

    def configure_optimizers(self):
        """Configure optimizer to be used by PyTorch Lightning for training."""
        return torch.optim.SGD(self.parameters(), lr=1e-4)

    def training_step(self, train_batch, batch_idx):
        """Configure train step used by PyTorch Lightning for training."""
        x, y = train_batch
        x = x.view(x.size(0), -1)
        y_hat = self.forward(x)
        loss = nn.CrossEntropyLoss(reduction='mean')(y_hat, y)
        self.log('train_loss', loss)
        return loss

    def validation_step(self, val_batch, batch_idx):
        """Configure val step used by PyTorch Lightning for validating."""
        x, y = val_batch
        x = x.view(x.size(0), -1)
        y_hat = self.forward(x)
        pred = y_hat.data.max(1, keepdim=True)[1]
        acc = pred.eq(y.data.view_as(pred)).sum()/y.size(0)
        loss = 1 - acc
        self.log('val_loss', loss)
        return loss
