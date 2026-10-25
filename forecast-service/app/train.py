"""Train the model with a correct (out-of-sample) evaluation and persist it.

Reports three views of quality:
  1. in-sample   - fit and evaluate on the same data (the old, optimistic way)
  2. hold-out    - 80/20 train/test split, metrics on the unseen 20 %
  3. 5-fold CV   - mean +- std of metrics on the held-out fold of each split
"""

import json
from pathlib import Path

import joblib
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import KFold, cross_validate, train_test_split

from .model import (
    CAT,
    NUM,
    TARGET,
    build_pipeline,
    load_training_data,
    train_model,
)


ARTIFACTS = (
    Path(__file__).resolve().parent.parent
    / "artifacts"
)

RANDOM_STATE = 42
TEST_SIZE = 0.2
CV_FOLDS = 5


def _scores(model, X, y) -> dict[str, float]:
    """Return R2 and MAE of a fitted model on the given data."""
    pred = model.predict(X)
    return {
        "r2": float(r2_score(y, pred)),
        "mae": float(mean_absolute_error(y, pred)),
    }


def main() -> None:
    """Evaluate the model correctly, then persist the final artifact."""

    df = load_training_data()
    X, y = df[NUM + CAT], df[TARGET]

    # 1. Baseline: in-sample evaluation (train and evaluate on the same data).
    in_sample = _scores(build_pipeline().fit(X, y), X, y)

    # 2. Hold-out: train only on the training split, evaluate on unseen data.
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=TEST_SIZE, random_state=RANDOM_STATE
    )
    holdout_model = build_pipeline().fit(X_train, y_train)
    train_scores = _scores(holdout_model, X_train, y_train)
    test_scores = _scores(holdout_model, X_test, y_test)

    # 3. K-fold cross-validation (every row is used for testing exactly once).
    cv = cross_validate(
        build_pipeline(),
        X,
        y,
        cv=KFold(n_splits=CV_FOLDS, shuffle=True, random_state=RANDOM_STATE),
        scoring=("r2", "neg_mean_absolute_error"),
        return_train_score=True,
    )
    cv_scores = {
        "r2_mean": float(cv["test_r2"].mean()),
        "r2_std": float(cv["test_r2"].std()),
        "mae_mean": float(-cv["test_neg_mean_absolute_error"].mean()),
        "mae_std": float(cv["test_neg_mean_absolute_error"].std()),
        "train_r2_mean": float(cv["train_r2"].mean()),
        "train_mae_mean": float(-cv["train_neg_mean_absolute_error"].mean()),
    }

    report = {
        "n_rows": int(len(df)),
        "in_sample": in_sample,
        "holdout_train": train_scores,
        "holdout_test": test_scores,
        "cv": cv_scores,
        "gap": {
            "r2_train_minus_test": train_scores["r2"] - test_scores["r2"],
            "mae_test_minus_train": test_scores["mae"] - train_scores["mae"],
        },
    }

    print(f"[train] rows: {report['n_rows']}")
    print(
        f"[train] in-sample (old)  : "
        f"R2={in_sample['r2']:.4f}, MAE={in_sample['mae']:.0f} USD"
    )
    print(
        f"[train] hold-out train   : "
        f"R2={train_scores['r2']:.4f}, MAE={train_scores['mae']:.0f} USD"
    )
    print(
        f"[train] hold-out TEST    : "
        f"R2={test_scores['r2']:.4f}, MAE={test_scores['mae']:.0f} USD"
    )
    print(
        f"[train] {CV_FOLDS}-fold CV (test)  : "
        f"R2={cv_scores['r2_mean']:.4f} +- {cv_scores['r2_std']:.4f}, "
        f"MAE={cv_scores['mae_mean']:.0f} +- {cv_scores['mae_std']:.0f} USD"
    )
    print(
        f"[train] gap train-test   : "
        f"dR2={report['gap']['r2_train_minus_test']:+.4f}, "
        f"dMAE={report['gap']['mae_test_minus_train']:+.0f} USD"
    )

    ARTIFACTS.mkdir(parents=True, exist_ok=True)

    metrics_path = ARTIFACTS / "metrics.json"
    metrics_path.write_text(json.dumps(report, indent=2))
    print(f"[train] metrics persisted: {metrics_path}")

    # Final artifact: refit on ALL data after the evaluation is done.
    # The metrics above (hold-out / CV) describe this same pipeline
    # and hyperparameters; the refit only gives it more data.
    final_model = train_model()

    artifact_path = ARTIFACTS / "model.pkl"
    joblib.dump(final_model, artifact_path)
    print(f"[train] artifact persisted: {artifact_path}")


if __name__ == "__main__":
    main()