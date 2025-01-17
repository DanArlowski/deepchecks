# ----------------------------------------------------------------------------
# Copyright (C) 2021 Deepchecks (https://www.deepchecks.com)
#
# This file is part of Deepchecks.
# Deepchecks is distributed under the terms of the GNU Affero General
# Public License (version 3 or later).
# You should have received a copy of the GNU Affero General Public License
# along with Deepchecks.  If not, see <http://www.gnu.org/licenses/>.
# ----------------------------------------------------------------------------
#
"""New Labels check tests"""
from copy import copy

from hamcrest import assert_that, close_to, has_entries, has_items, has_length, equal_to

from deepchecks.vision.checks import NewLabels
from deepchecks.vision.utils.test_utils import get_modified_dataloader
from tests.base.utils import equal_condition_result


def get_modification_func_classification(new_labels):
    def add_new_test_labels(orig_dataset, idx):
        if idx % 7 == 0:
            data, label = orig_dataset[idx]
            return data, new_labels[idx % 5]
        else:
            return orig_dataset[idx]

    return add_new_test_labels


def get_modification_func_classification_switch_single_label():
    def add_new_test_labels(orig_dataset, idx):
        data, label = orig_dataset[idx]
        if label == 3:
            return data, -3
        else:
            return orig_dataset[idx]

    return add_new_test_labels


def get_modification_func_object_detection(new_labels):
    def add_new_test_labels(orig_dataset, idx):
        if idx % 7 == 0:
            data, label = orig_dataset[idx]
            if label.shape[0] > 0:
                label[0, -1] = new_labels[idx % 5]
            return data, label
        else:
            return orig_dataset[idx]

    return add_new_test_labels


def test_object_detection_coco(coco_train_visiondata, coco_test_visiondata, device):
    # Act
    result = NewLabels().run(coco_train_visiondata, coco_test_visiondata, device=device)
    # Assert
    assert_that(result.value['new_labels'], has_entries({'donut': 14, 'tennis racket': 7}))
    assert_that(result.value, has_entries(all_labels_count=387))


def test_object_detection_coco_with_condition(coco_train_visiondata, coco_test_visiondata, device):
    # Act
    check = NewLabels().add_condition_new_label_ratio_not_greater_than(0.1)
    result = check.conditions_decision(check.run(coco_train_visiondata, coco_test_visiondata, device=device))
    # Assert
    assert_that(result, has_items(
        equal_condition_result(
            is_pass=False,
            name='Percentage of new labels in the test set not above 10%.',
            details=(
                '10.85% of labels found in test set were not in train set. '
                'New labels most common in test set: [\'donut\', \'tennis racket\', \'boat\']'))
    ))


def test_object_detection_coco_new_labels(coco_train_visiondata, coco_test_visiondata, device):
    # Arrange
    test = copy(coco_test_visiondata)
    new_labels = [-1, -2, -3, -4, -5]
    test._data_loader = get_modified_dataloader(test, get_modification_func_object_detection(new_labels))
    # Act
    result = NewLabels().run(coco_train_visiondata, test, device=device)
    # Assert
    assert_that(result.value['new_labels'], has_entries({'donut': 14, 'tennis racket': 7}))
    assert_that(result.value, has_entries(all_labels_count=387))


def test_classification_mnist_with_condition(mnist_dataset_train, mnist_dataset_test, device):
    # Arrange
    check = NewLabels().add_condition_new_label_ratio_not_greater_than(0)
    # Act
    result = check.run(mnist_dataset_train, mnist_dataset_test, device=device)
    # Assert
    assert_that(check.conditions_decision(result), has_items(
        equal_condition_result(is_pass=True,
                               name='Percentage of new labels in the test set not above 0%.',
                               details='No new labels were found in test set.')
    ))
    assert_that(result.value['new_labels'], has_length(0))


def test_classification_mnist_change_label(mnist_dataset_train, mnist_dataset_test, device):
    # Arrange
    test = copy(mnist_dataset_test)
    test._data_loader = get_modified_dataloader(test, get_modification_func_classification_switch_single_label())
    # Act
    result = NewLabels().run(mnist_dataset_train, test, device=device)
    # Assert
    assert_that(result.value, equal_to({'new_labels': {'-3': 1010}, 'all_labels_count': 10000}))


def test_classification_mnist_change_label_with_condition(mnist_dataset_train, mnist_dataset_test, device):
    # Arrange
    test = copy(mnist_dataset_test)
    test._data_loader = get_modified_dataloader(test, get_modification_func_classification_switch_single_label())
    check = NewLabels().add_condition_new_label_ratio_not_greater_than(0)
    # Act
    result = check.run(mnist_dataset_train, test, device=device)
    # Assert
    assert_that(check.conditions_decision(result), has_items(
        equal_condition_result(is_pass=False,
                               name='Percentage of new labels in the test set not above 0%.',
                               details='10.1% of labels found in test set were not in train set.'
                                       ' New labels most common in test set: [\'-3\']')
    ))
    assert_that(result.value, equal_to({'new_labels': {'-3': 1010}, 'all_labels_count': 10000}))


def test_classification_mnist_new_labels(mnist_dataset_train, mnist_dataset_test, device):
    # Arrange
    test = copy(mnist_dataset_test)
    new_labels = [-1, -2, -3, -4, -5]
    test._data_loader = get_modified_dataloader(test, get_modification_func_classification(new_labels))
    # Act
    result = NewLabels().run(mnist_dataset_train, test, device=device)
    # Assert
    assert_that(result.value, equal_to({'new_labels': {'-5': 286, '-3': 286, '-1': 286, '-2': 286, '-4': 285},
                                        'all_labels_count': 10000}))
