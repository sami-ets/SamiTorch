# -*- coding: utf-8 -*-
# Copyright 2019 SAMITorch Authors. All Rights Reserved.
#
# Licensed under the MIT License;
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://opensource.org/licenses/MIT
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ==============================================================================


import torch


def to_onehot(indices, num_classes):
    """Convert a tensor of indices of any shape `(N, ...)` to a tensor of one-hot indicators of shape
    `(N, num_classes, ...)`."""
    onehot = torch.zeros(indices.shape[0], num_classes, *indices.shape[1:], device=indices.device)
    return onehot.scatter_(1, indices.unsqueeze(1), 1)