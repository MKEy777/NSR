import pytest
import torch

from common.config import DATASET_CONFIGS
from common.model_builder import MODEL_NAMES, build_model


def test_efficientnet_b3_is_removed_from_registry():
    assert "efficientnet_b3" not in MODEL_NAMES
    with pytest.raises(ValueError, match="efficientnet_b3"):
        build_model("efficientnet_b3", "seed", torch.device("cpu"))


@pytest.mark.parametrize("model_name", MODEL_NAMES)
def test_all_registered_models_build_and_run(model_name):
    cfg = DATASET_CONFIGS["seed"]
    model = build_model(model_name, "seed", torch.device("cpu"))
    model.eval()

    x = torch.rand(2, *cfg.input_shape)
    with torch.no_grad():
        out = model(x)
    if isinstance(out, tuple):
        out = out[0]

    assert out.shape == (2, cfg.num_classes)
    assert model.__class__.__name__ not in {"AdaptiveImageClassifier", "FlattenSNNAdapter"}
