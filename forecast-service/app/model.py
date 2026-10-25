"""Definition of the model and preprocessing pipeline for Ames Housing."""

from pathlib import Path

import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


DATA_PATH = (
    Path(__file__).resolve().parent.parent
    / "data"
    / "ames_train.csv"
)

# Internal feature names used by the model.
# These names match the API-to-model contract.
NUM = [
    "GrLivArea",
    "TotalBsmtSF",
    "GarageArea",
    "YearBuilt",
    "OverallQual",
]

CAT = ["MSZoning"]
TARGET = "SalePrice"

# Column names used by the Ames Housing CSV.
CSV_COLUMNS = {
    "Gr Liv Area": "GrLivArea",
    "Total Bsmt SF": "TotalBsmtSF",
    "Garage Area": "GarageArea",
    "Year Built": "YearBuilt",
    "Overall Qual": "OverallQual",
    "MS Zoning": "MSZoning",
    "SalePrice": "SalePrice",
}


def load_training_data() -> pd.DataFrame:
    """Load and normalize the Ames Housing training dataset.

    The source CSV may use column names with or without spaces,
    depending on which variant of the dataset is provided. Both are
    normalized to the space-free names used internally by the model.
    """
    df = pd.read_csv(DATA_PATH)

    # Remove all whitespace from column names, so both
    # "Gr Liv Area" and "GrLivArea" normalize to "GrLivArea".
    df.columns = df.columns.str.replace(" ", "", regex=False).str.strip()

    columns = NUM + CAT + [TARGET]
    missing_columns = set(columns) - set(df.columns)

    if missing_columns:
        raise ValueError(
            "Training dataset is missing required columns: "
            f"{sorted(missing_columns)}"
        )

    return df[columns].dropna(subset=[TARGET])


def build_pipeline() -> Pipeline:
    """Build an UNFITTED Ridge regression pipeline.

    Numerical features are imputed using the median and standardized.
    Categorical features are imputed using the most frequent value and
    one-hot encoded, with unknown categories ignored during inference.

    All preprocessing lives inside the pipeline, so during train/test
    split and cross-validation the imputers, scaler and encoder are fitted
    only on the training part (no data leakage).
    """
    preprocessor = ColumnTransformer(
        [
            (
                "num",
                Pipeline(
                    [
                        ("imputer", SimpleImputer(strategy="median")),
                        ("scaler", StandardScaler()),
                    ]
                ),
                NUM,
            ),
            (
                "cat",
                Pipeline(
                    [
                        (
                            "imputer",
                            SimpleImputer(strategy="most_frequent"),
                        ),
                        (
                            "onehot",
                            OneHotEncoder(handle_unknown="ignore"),
                        ),
                    ]
                ),
                CAT,
            ),
        ]
    )

    return Pipeline(
        [
            ("preprocess", preprocessor),
            ("regressor", Ridge(alpha=1.0)),
        ]
    )


def train_model() -> Pipeline:
    """Build the pipeline and fit it on ALL data.

    Used by the dev-only fallback in main.py and for the final artifact.
    """
    df = load_training_data()

    pipe = build_pipeline()
    pipe.fit(df[NUM + CAT], df[TARGET])

    return pipe