# The Complete Machine Learning Course
### A Step-by-Step Practical Guide: From First Model to Production ML Systems

**Format:** Self-paced manual · **Duration:** ~14 weeks (or your pace) · **Prerequisite:** Basic Python

---

## How to Use This Manual

Every module follows the same structure:

1. **Concept** — what you're learning and why it matters
2. **Problem Statement** — a concrete scenario you'll solve
3. **Solution Walkthrough** — step-by-step implementation with runnable code
4. **Exercise** — build something yourself before moving on
5. **Checkpoint** — self-test: "Can I do X?" If no, repeat the module.

**Rules for success:**
- Type the code yourself. Run it. Change it. Break it.
- Every module uses real or realistic data — no toy `[1,2,3]` arrays after Module 2.
- Keep one project folder (`ml-course/`), one subfolder per module.
- The most important habit in ML: **look at your data before modeling, and look at your errors after.** This course drills that in every module.

---

## Course Roadmap

| Part | Modules | What You'll Be Able to Do After |
|------|---------|--------------------------------|
| **0. Setup** | 0 | Working environment; just-enough math |
| **1. Foundations** | 1–4 | Load/clean/explore data; train, evaluate, and NOT fool yourself |
| **2. Core Supervised Learning** | 5–9 | Regression, classification, trees, gradient boosting, feature engineering, honest validation |
| **3. Unsupervised Learning** | 10–11 | Clustering, dimensionality reduction, anomaly detection |
| **4. Three Real Projects** | 12–14 | Ship complete churn, pricing, and NLP projects end-to-end |
| **5. Deep Learning** | 15–18 | Neural nets from scratch → PyTorch → CNNs → transformers & transfer learning |
| **6. Specialized Domains** | 19–22 | Time series, recommenders, NLP with embeddings/LLMs, imbalanced & tabular tricks |
| **7. Production MLOps** | 23–25 | Pipelines, deployment, monitoring, drift, retraining |
| **8. Use Case Catalog** | — | 100+ real-world use cases: problem → solution → build steps |
| **9. Capstones** | — | 5 portfolio projects + 14-week plan + troubleshooting guide |

---

# PART 0 — SETUP

## Module 0: Environment + Just-Enough Math

### Step-by-Step Setup

**Step 1 — Python 3.11+ and a project:**
```bash
mkdir ml-course && cd ml-course
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install numpy pandas scikit-learn matplotlib seaborn jupyter
# later modules add: xgboost lightgbm torch torchvision statsmodels shap mlflow fastapi
```

**Step 2 — Verify:**
```python
# module0/hello_ml.py
import numpy as np, pandas as pd, sklearn
print(np.__version__, pd.__version__, sklearn.__version__)

from sklearn.datasets import load_diabetes
X, y = load_diabetes(return_X_y=True)
print("data loaded:", X.shape, y.shape)   # (442, 10) (442,)
```

**Step 3 — Choose your workspace.** Jupyter notebooks (`jupyter lab`) for exploration; `.py` scripts for anything you'll reuse. This course shows scripts; run them cell-style in Jupyter if you prefer.

### Just-Enough Math (seriously, this is enough to start)

You need working intuition for four things. Learn deeper math *as models demand it*, not before:

1. **Vectors & matrices** — a dataset is a matrix: rows = examples, columns = features. Model math is mostly matrix multiplication. If you can read `X @ w + b`, you're ready.
2. **Derivatives = "which direction improves things"** — training is: measure error, compute the slope of error w.r.t. each parameter (gradient), step downhill. That's gradient descent, and it's 90% of the calculus you need.
3. **Probability basics** — a classifier outputs P(class | features). Know what a distribution, mean, variance, and conditional probability are.
4. **The one statistics idea that rules ML:** performance on data you trained on is a lie. Everything in Module 4 exists because of this sentence.

```python
# module0/gradient_descent_in_10_lines.py — the beating heart of ML
import numpy as np
X = np.array([[1.0], [2.0], [3.0], [4.0]])     # feature: hours studied
y = np.array([2.1, 3.9, 6.2, 7.8])             # target: score
w, b, lr = 0.0, 0.0, 0.01
for step in range(2000):
    pred = X[:, 0] * w + b
    error = pred - y
    w -= lr * (2 * error * X[:, 0]).mean()      # gradient of MSE w.r.t. w
    b -= lr * (2 * error).mean()                # gradient of MSE w.r.t. b
print(f"learned: y ≈ {w:.2f}x + {b:.2f}")       # ≈ 1.93x + 0.18
```
Run it. You just trained a model with gradient descent, by hand. Every model in this course — up to billion-parameter networks — is this loop with fancier `pred`.

### Checkpoint ✅
- [ ] Environment runs; I trained the 10-line model and can explain each line
- [ ] I can state why training-data performance is misleading

---

# PART 1 — FOUNDATIONS

## Module 1: What ML Is (and Isn't)

### Concept
**Machine learning = learning a function from examples instead of writing rules.**

```
Traditional:  rules + data → answers        (you write the logic)
ML:           data + answers → rules        (the algorithm finds the logic)
```

Use ML when: the rules are too complex to write (spam, vision), the rules change (fraud), or personalization is needed at scale. **Don't** use ML when a lookup table, a regex, or an if-statement works — the best ML engineers are distinguished by how often they *don't* use ML.

The three learning paradigms:
| Paradigm | Data looks like | Example |
|---|---|---|
| **Supervised** | (features, label) pairs | spam/not-spam, house prices |
| **Unsupervised** | features only, no labels | customer segments, anomalies |
| **Reinforcement** | reward signals from actions | game playing, robotics (out of scope; pointers at the end) |

Supervised splits into **classification** (predict a category) and **regression** (predict a number). ~80% of industry ML is supervised learning on tables — which is why this course spends its weight there, not on chatbot demos.

### Problem Statement
Classify these as ML-appropriate or not, and name the paradigm + task type: (a) predict tomorrow's electricity demand, (b) validate email address format, (c) group news articles by topic without predefined topics, (d) estimate probability a loan defaults, (e) convert USD to EUR at today's rate.

### Solution
(a) ML — supervised regression (time series flavor, Module 19). (b) NOT ML — regex. (c) ML — unsupervised clustering. (d) ML — supervised classification (probability output). (e) NOT ML — multiplication. If you said ML for (b) or (e), recalibrate: deterministic rules beat learned approximations every time they're available.

### Checkpoint ✅
- [ ] Given a business problem, I can say: ML or not, and if ML, which paradigm and task type

---

## Module 2: Data Handling with Pandas (The Real Job)

### Concept
Practitioners spend 60–80% of their time on data, not models. Master this module and you're ahead of most bootcamp graduates. Core skills: load, inspect, clean, transform, join, aggregate.

### Problem Statement
You receive `telecom_churn.csv` (realistic mess: missing values, wrong dtypes, duplicates, a leaky column). Produce a clean analysis-ready DataFrame and a written data quality report.

### Solution Walkthrough

**Step 1 — Get real data.** Download the Telco Customer Churn dataset (widely mirrored, e.g., on Kaggle: "Telco Customer Churn") or generate a stand-in:
```python
# module2/make_data.py — creates a realistic messy dataset if you're offline
import numpy as np, pandas as pd
rng = np.random.default_rng(42)
n = 7000
df = pd.DataFrame({
    "customerID": [f"C{i:05d}" for i in range(n)],
    "tenure": rng.integers(0, 72, n),
    "MonthlyCharges": rng.uniform(18, 120, n).round(2),
    "Contract": rng.choice(["Month-to-month", "One year", "Two year"], n, p=[.55,.25,.2]),
    "InternetService": rng.choice(["DSL", "Fiber optic", "No"], n),
    "SeniorCitizen": rng.choice([0, 1], n, p=[.84,.16]),
})
df["TotalCharges"] = (df.tenure * df.MonthlyCharges * rng.uniform(.9,1.1,n)).round(2)
churn_p = (0.42 - 0.004*df.tenure + 0.12*(df.Contract=="Month-to-month")
           + 0.08*(df.InternetService=="Fiber optic")).clip(0.02, 0.9)
df["Churn"] = np.where(rng.uniform(size=n) < churn_p, "Yes", "No")
# inject realistic mess:
df.loc[rng.choice(n, 60, replace=False), "TotalCharges"] = " "        # blanks as spaces!
df = pd.concat([df, df.sample(25, random_state=1)])                    # duplicates
df["CancellationDate"] = np.where(df.Churn=="Yes", "2026-05-01", "")   # LEAKY column
df.to_csv("telecom_churn.csv", index=False)
```

**Step 2 — Inspect before touching anything** (make this reflexive):
```python
# module2/clean.py
import pandas as pd
df = pd.read_csv("telecom_churn.csv")

print(df.shape)                 # rows, cols
print(df.head())
print(df.dtypes)                # TotalCharges will be 'object' — a red flag
print(df.isna().sum())
print(df.duplicated(subset="customerID").sum())
print(df.describe(include="all").T)
```

**Step 3 — Fix, with reasons:**
```python
# 3a. Duplicates: keep first occurrence
df = df.drop_duplicates(subset="customerID", keep="first")

# 3b. TotalCharges is text because of " " blanks → coerce, then decide on NaNs
df["TotalCharges"] = pd.to_numeric(df["TotalCharges"], errors="coerce")
print("missing after coerce:", df.TotalCharges.isna().sum())
# Rule: understand WHY missing before filling. Here: blanks ≈ brand-new customers.
df["TotalCharges"] = df["TotalCharges"].fillna(0)

# 3c. THE LEAK: CancellationDate is only known AFTER churn happens.
# Any model using it "predicts" churn perfectly and is useless in production.
df = df.drop(columns=["CancellationDate"])

# 3d. Types: categories as category dtype (memory + clarity)
for c in ["Contract", "InternetService", "Churn"]:
    df[c] = df[c].astype("category")

df.to_parquet("churn_clean.parquet")   # parquet > csv for everything downstream
```

**Step 4 — The data quality report** (one paragraph, every project, forever): rows in/out, duplicates removed, missingness per column + fill strategy + rationale, dropped columns + why, remaining concerns. This paragraph is what separates professionals from notebook tourists.

**Leakage — the #1 silent killer in applied ML.** A leaky feature contains information unavailable at prediction time (post-outcome timestamps, aggregates computed over the full history including the future, the label in disguise). Symptom: validation accuracy that's suspiciously great. You'll formally hunt leaks in Module 4 and get burned by one on purpose in Module 12.

### Exercise
Add three more pathologies to the generator (an outlier, an inconsistent category spelling like "fiber optic", a column that's 95% missing) and extend your cleaner to handle them with documented decisions.

### Checkpoint ✅
- [ ] I inspect shape/dtypes/missingness/duplicates before any analysis, automatically
- [ ] I can define leakage and give two examples from my own domain

---

## Module 3: EDA — Exploratory Data Analysis

### Concept
EDA answers three questions before modeling: **What does each variable look like? How do features relate to the target? What will bite me later?** Skipping EDA is how you ship a model that predicts everyone churns because you never noticed the 90/10 class imbalance.

### Problem Statement
On your cleaned churn data: produce the standard EDA battery and extract 3 modeling-relevant insights.

### Solution Walkthrough
```python
# module3/eda.py
import pandas as pd, matplotlib.pyplot as plt, seaborn as sns
df = pd.read_parquet("churn_clean.parquet")

# 1. Target balance — determines your metrics (Module 4) and methods (Module 22)
print(df.Churn.value_counts(normalize=True))     # e.g. No 0.72 / Yes 0.28

# 2. Numeric distributions — skew? outliers? weird spikes?
df[["tenure", "MonthlyCharges", "TotalCharges"]].hist(bins=40, figsize=(12,3))
plt.savefig("distributions.png")

# 3. Feature vs target — the money plots
fig, ax = plt.subplots(1, 2, figsize=(12,4))
sns.boxplot(data=df, x="Churn", y="tenure", ax=ax[0])
pd.crosstab(df.Contract, df.Churn, normalize="index").plot.bar(stacked=True, ax=ax[1])
plt.savefig("target_relations.png")

# 4. Correlations (numeric) — collinearity heads-up
print(df[["tenure","MonthlyCharges","TotalCharges"]].corr().round(2))

# 5. Grouped rates — the tables stakeholders actually understand
print(df.groupby("Contract", observed=True).Churn
        .apply(lambda s: (s=="Yes").mean()).round(3))
```

Typical findings on this data (yours will be similar): churners cluster at low tenure; month-to-month contracts churn ~4× two-year contracts; `TotalCharges ≈ tenure × MonthlyCharges` (near-duplicate information — expect collinearity); classes are imbalanced ~72/28 → accuracy alone will mislead (Module 4 fixes this).

**The EDA checklist to reuse forever:** target distribution → each feature's distribution → feature-vs-target → correlations → missingness patterns → time patterns if any timestamp exists → "too good to be true" features (leak suspects).

### Exercise
Write `eda_report(df, target)` — a function producing the whole battery for any dataset. You'll use it in every project for the rest of this course (and career).

### Checkpoint ✅
- [ ] I found the imbalance, the collinearity, and the tenure effect myself
- [ ] I have a reusable EDA function

---

## Module 4: Train/Test Discipline & Metrics (Where Careers Are Made)

### Concept
The cardinal rule: **evaluate on data the model has never seen, under conditions matching production.** Everything else in this module is machinery to obey that rule honestly:

```
             ┌── TRAIN (fit the model)
ALL DATA ────┼── VALIDATION (tune choices: features, hyperparams)
             └── TEST (touch ONCE, at the very end — your honest estimate)
```

And the metric zoo — choose based on the *cost structure* of mistakes, not habit:

| Task | Metric | Use when |
|---|---|---|
| Classification | **Accuracy** | Classes balanced AND errors cost the same (rare!) |
| | **Precision** | False positives are costly (spam filter blocking real mail) |
| | **Recall** | False negatives are costly (cancer screening, fraud) |
| | **F1** | Need one number balancing precision/recall |
| | **ROC-AUC** | Ranking quality across thresholds; imbalance-tolerant-ish |
| | **PR-AUC** | Like AUC but honest under heavy imbalance |
| | **Log loss / calibration** | You need trustworthy probabilities (pricing, risk) |
| Regression | **MAE** | Errors hurt linearly; robust to outliers |
| | **RMSE** | Big errors hurt disproportionately |
| | **MAPE** | Stakeholders think in %; beware zeros |
| | **R²** | Variance explained; fine for reporting, poor for optimizing |

### Problem Statement
Train a churn classifier that reports 94% accuracy and is nonetheless garbage. Then evaluate it honestly and fix the evaluation.

### Solution Walkthrough

**Step 1 — The garbage-but-94% model:**
```python
# module4/honest_eval.py
import pandas as pd, numpy as np
from sklearn.model_selection import train_test_split
from sklearn.dummy import DummyClassifier
from sklearn.metrics import (accuracy_score, precision_score, recall_score,
                             f1_score, roc_auc_score, confusion_matrix,
                             classification_report)

df = pd.read_parquet("churn_clean.parquet")
# make imbalance harsher to prove the point: subsample churners
churn = df[df.Churn=="Yes"].sample(frac=0.25, random_state=0)
df_imb = pd.concat([df[df.Churn=="No"], churn])
y = (df_imb.Churn == "Yes").astype(int)
X = df_imb[["tenure", "MonthlyCharges", "TotalCharges"]]

X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2,
                                          stratify=y, random_state=42)
dummy = DummyClassifier(strategy="most_frequent").fit(X_tr, y_tr)
print("accuracy:", accuracy_score(y_te, dummy.predict(X_te)))   # ~0.93 😱
print("recall:  ", recall_score(y_te, dummy.predict(X_te)))     # 0.0 — catches NO churners
```
A model that never predicts churn scores 93% accuracy. **Always establish the dummy baseline first** — every real model must beat it, and it defines what accuracy even means on your data.

**Step 2 — Honest evaluation of a real model:**
```python
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline

model = make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000))
model.fit(X_tr, y_tr)
proba = model.predict_proba(X_te)[:, 1]
pred  = (proba >= 0.5).astype(int)

print(confusion_matrix(y_te, pred))          # the four numbers that tell the truth
print(classification_report(y_te, pred))
print("ROC-AUC:", roc_auc_score(y_te, proba).round(3))
```
Read the confusion matrix aloud: "Of N actual churners, we caught TP and missed FN." That sentence is the model's business value.

**Step 3 — Thresholds are a business decision, not 0.5:**
```python
for t in [0.3, 0.5, 0.7]:
    p = (proba >= t).astype(int)
    print(f"t={t}: precision={precision_score(y_te,p):.2f} recall={recall_score(y_te,p):.2f}")
```
Retention team can call 200 customers/month? Pick the threshold that fills 200 slots with maximum expected saves. The model gives probabilities; **the business picks the operating point.**

**Step 4 — Cross-validation** (when data is limited or you want stability estimates):
```python
from sklearn.model_selection import cross_val_score, StratifiedKFold
cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
scores = cross_val_score(model, X_tr, y_tr, cv=cv, scoring="roc_auc")
print(f"CV AUC: {scores.mean():.3f} ± {scores.std():.3f}")
```
CV replaces the validation split for tuning. The held-out test set still gets touched exactly once at the end.

**Step 5 — Splits must mimic production:**
- **Time-based data → split by time** (train on past, test on future). Random splits on temporal data are leakage.
- **Grouped data → split by group** (all records of one customer/patient on the same side; `GroupKFold`). Otherwise the model memorizes individuals.
- **Stratify** classification splits so class ratios hold.
This trio prevents the most common catastrophic evaluation errors in industry.

### Exercise
Take your churn data with a fake `signup_date` column (generate one correlated with tenure). Show that a random split gives a better score than a time-based split, and explain in two sentences why the time-based number is the truthful one.

### Checkpoint ✅
- [ ] I always fit a dummy baseline first
- [ ] I can choose a metric from an error-cost description and defend it
- [ ] I know when to split by time or by group, and why

---

# PART 2 — CORE SUPERVISED LEARNING

## Module 5: Linear Models (Underrated Forever)

### Concept
**Linear regression:** `y = w·x + b` — fit by minimizing squared error (your Module 0 loop, vectorized).
**Logistic regression:** same linear score squeezed through a sigmoid → probability. Despite the name, it's a classifier.
Why masters keep them close: fast, stable, interpretable coefficients, hard to overfit with regularization, killer baselines, and the building block of neural nets.

**Regularization = penalizing large weights to prevent overfitting:**
- **Ridge (L2):** shrinks all weights smoothly. Default choice.
- **Lasso (L1):** shrinks some weights to exactly zero → built-in feature selection.
- The strength knob (`alpha`/`C`) is your first hyperparameter — tuned on validation, never test.

### Problem Statement
Predict house prices on the California Housing dataset; interpret which factors drive price; demonstrate regularization rescuing an overfit model.

### Solution Walkthrough
```python
# module5/linear.py
import numpy as np
from sklearn.datasets import fetch_california_housing
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.linear_model import LinearRegression, Ridge, Lasso
from sklearn.preprocessing import StandardScaler, PolynomialFeatures
from sklearn.pipeline import make_pipeline
from sklearn.metrics import mean_absolute_error

X, y = fetch_california_housing(return_X_y=True, as_frame=True)
X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2, random_state=42)

# 1. Baseline: predict the mean
print("dummy MAE:", mean_absolute_error(y_te, np.full(len(y_te), y_tr.mean())).round(3))

# 2. Plain linear regression (ALWAYS scale features for linear models)
lin = make_pipeline(StandardScaler(), LinearRegression()).fit(X_tr, y_tr)
print("linear MAE:", mean_absolute_error(y_te, lin.predict(X_te)).round(3))

# 3. Interpret: standardized coefficients = feature influence
coefs = dict(zip(X.columns, lin[-1].coef_.round(2)))
print(sorted(coefs.items(), key=lambda kv: -abs(kv[1])))
# MedInc dominates; Latitude/Longitude matter (location, location, location)

# 4. Manufacture overfitting: degree-3 polynomial features (8 cols → 160+)
poly = make_pipeline(StandardScaler(), PolynomialFeatures(3), LinearRegression())
poly.fit(X_tr, y_tr)
print("poly train MAE:", mean_absolute_error(y_tr, poly.predict(X_tr)).round(3))  # great
print("poly test  MAE:", mean_absolute_error(y_te, poly.predict(X_te)).round(3))  # worse/unstable

# 5. Ridge to the rescue — same features, penalized weights
ridge = make_pipeline(StandardScaler(), PolynomialFeatures(3), Ridge(alpha=10.0))
ridge.fit(X_tr, y_tr)
print("ridge test MAE:", mean_absolute_error(y_te, ridge.predict(X_te)).round(3))
```

**The bias–variance intuition you just witnessed:** simple models underfit (high bias — can't capture the pattern); overly flexible models overfit (high variance — memorize noise). Regularization, more data, and simpler models pull variance down; richer features and flexible models pull bias down. Every modeling decision for the rest of your career is navigating this trade.

**Diagnostic you'll use forever:** train score vs validation score. Both bad → underfitting (add capacity/features). Train great, validation bad → overfitting (regularize, simplify, get data). Close and good → ship it.

### Exercise
Sweep `alpha` over `[0.01, 0.1, 1, 10, 100, 1000]` with CV, plot validation MAE vs alpha (log x-axis). Find the U-shape. Then swap Ridge→Lasso and print which features it zeroed out.

### Checkpoint ✅
- [ ] I can read coefficients and explain the model to a stakeholder
- [ ] I can diagnose under/overfitting from train-vs-validation scores
- [ ] I tuned my first hyperparameter with CV

---

## Module 6: Trees, Random Forests & Gradient Boosting (The Tabular Kings)

### Concept
**Decision tree:** learned flowchart of if/else splits. Interpretable, handles nonlinearity and interactions natively, needs no scaling — but a single deep tree overfits savagely.
**Random forest:** hundreds of trees, each on a bootstrap sample with random feature subsets; predictions averaged. Variance evaporates. Robust, hard to mess up.
**Gradient boosting (XGBoost/LightGBM):** trees built *sequentially*, each correcting the previous ensemble's errors — your Module 0 gradient descent, but each "step" is a whole tree. **On tabular data, tuned gradient boosting is still the strongest default in industry — it beats deep learning on most tables.** Internalize that before reaching for neural nets.

### Problem Statement
Full churn model on your Module 2 data: tree vs forest vs boosting, tuned honestly, with feature importance the business can act on.

### Solution Walkthrough
```python
# module6/trees.py     pip install lightgbm
import pandas as pd
from sklearn.model_selection import train_test_split, RandomizedSearchCV, StratifiedKFold
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import roc_auc_score
import lightgbm as lgb

df = pd.read_parquet("churn_clean.parquet")
y = (df.Churn == "Yes").astype(int)
X = pd.get_dummies(df.drop(columns=["Churn", "customerID"]), drop_first=True)
X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2, stratify=y, random_state=42)

def auc(model):  # fit + honest score
    model.fit(X_tr, y_tr)
    return roc_auc_score(y_te, model.predict_proba(X_te)[:, 1]).round(4)

print("tree (unlimited):", auc(DecisionTreeClassifier(random_state=0)))         # overfits
print("tree (depth=4):  ", auc(DecisionTreeClassifier(max_depth=4, random_state=0)))
print("random forest:   ", auc(RandomForestClassifier(n_estimators=300, random_state=0)))
print("lightgbm default:", auc(lgb.LGBMClassifier(random_state=0, verbose=-1)))

# Tune LightGBM properly — random search beats grid search per compute spent
params = {
    "num_leaves": [15, 31, 63, 127],
    "learning_rate": [0.01, 0.03, 0.1],
    "n_estimators": [200, 500, 1000],
    "min_child_samples": [10, 20, 50],
    "subsample": [0.7, 0.9, 1.0],
    "colsample_bytree": [0.7, 0.9, 1.0],
}
search = RandomizedSearchCV(
    lgb.LGBMClassifier(random_state=0, verbose=-1), params, n_iter=30,
    scoring="roc_auc", cv=StratifiedKFold(5, shuffle=True, random_state=1),
    random_state=2, n_jobs=-1)
search.fit(X_tr, y_tr)
print("tuned CV AUC:", round(search.best_score_, 4), search.best_params_)
print("tuned TEST AUC:", roc_auc_score(y_te, search.best_estimator_.predict_proba(X_te)[:,1]).round(4))
```

**Feature importance — do it right:** built-in `feature_importances_` is biased toward high-cardinality features. Use **permutation importance** (shuffle one column, measure the score drop) for honest answers, and SHAP for per-prediction explanations:
```python
from sklearn.inspection import permutation_importance
r = permutation_importance(search.best_estimator_, X_te, y_te,
                           scoring="roc_auc", n_repeats=10, random_state=0)
for i in r.importances_mean.argsort()[::-1][:8]:
    print(f"{X.columns[i]:<35} {r.importances_mean[i]:.4f}")
```

**Practical wisdom to keep:**
- Order of attack on any tabular problem: dummy → logistic regression → LightGBM default → LightGBM tuned. The gaps between those four numbers tell you where the value is.
- Boosting hyperparameters that matter most: `learning_rate` × `n_estimators` (lower rate + more trees + early stopping), `num_leaves`/`max_depth`, `min_child_samples`.
- Forests parallelize and rarely overfit; boosting squeezes out the last points but needs tuning care.

### Exercise
Add early stopping with a validation set (`lgb` `callbacks=[lgb.early_stopping(50)]`) and show it finds the right tree count automatically. Then deliberately re-add the leaky `CancellationDate` from Module 2 as a feature and watch AUC hit ~1.0 — your first leak detection by "too good to be true."

### Checkpoint ✅
- [ ] I know the 4-model order of attack and ran it
- [ ] I can explain boosting vs bagging in two sentences
- [ ] I used permutation importance and can present the top drivers

---

## Module 7: Feature Engineering (Where Wins Actually Come From)

### Concept
On tabular problems, **better features beat better algorithms**, almost always. Categories of transformation:

| Technique | When | Tool |
|---|---|---|
| One-hot encoding | Low-cardinality categoricals | `OneHotEncoder` / `get_dummies` |
| Target/ordinal encoding | High-cardinality categoricals (zip codes) | `TargetEncoder` (careful: fit inside CV or it leaks) |
| Scaling | Linear models, neural nets, k-NN, SVM (trees don't care) | `StandardScaler` |
| Log/power transforms | Skewed numerics (income, prices) | `np.log1p`, `PowerTransformer` |
| Binning | Nonlinear effects for linear models; robustness | `KBinsDiscretizer` |
| Date decomposition | Any timestamp | month, day-of-week, hour, is-weekend, days-since |
| Interactions & ratios | Domain knowledge in feature form | `charges/tenure`, `debt/income` |
| Aggregations | Entity history (per customer: count, mean, recency) | `groupby` + merge |
| Text basics | Short text fields | length, keyword flags, TF-IDF (Module 21 goes deeper) |
| Missingness flags | When missing is informative | `X["col_missing"] = X.col.isna()` |

### Problem Statement
Beat your tuned Module 6 LightGBM using *feature engineering only* — same algorithm, same tuning budget.

### Solution Walkthrough
```python
# module7/features.py — engineered features for churn
import numpy as np, pandas as pd
df = pd.read_parquet("churn_clean.parquet")

f = df.copy()
# Ratios & rates (domain logic: value intensity)
f["avg_monthly"] = f.TotalCharges / f.tenure.clip(lower=1)
f["charge_delta"] = f.MonthlyCharges - f.avg_monthly      # recent price increase?
# Lifecycle stages (nonlinearity as a category)
f["tenure_bucket"] = pd.cut(f.tenure, [-1, 6, 12, 24, 48, 100],
                            labels=["0-6m","6-12m","1-2y","2-4y","4y+"])
# Interactions the tree might not find with limited data
f["new_and_monthly"] = ((f.tenure < 6) & (f.Contract=="Month-to-month")).astype(int)
f["fiber_senior"]    = ((f.InternetService=="Fiber optic") & (f.SeniorCitizen==1)).astype(int)
```
Rebuild the Module 6 pipeline with these added; re-run the same RandomizedSearch. Typical result on this data: **+0.01–0.03 AUC — more than most algorithm swaps deliver.**

**The professional workflow (memorize the loop):**
```
hypothesize (domain reasoning) → build feature → validate with CV →
keep if it helps, delete if not → LOOK AT ERRORS → hypothesize again
```
**Error analysis, the step everyone skips:** pull the 30 validation cases with the worst predictions. Read them like a detective. Patterns you find ("we're wrong about high-tenure churners — they all had a recent charge_delta spike") become your next features. One hour of error analysis outperforms a day of hyperparameter tuning.

**Leak-safe engineering rules:** every statistic computed *from data* (target encodings, aggregation means, scalers) must be fit on training folds only — which is exactly why sklearn **Pipelines** exist:
```python
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.pipeline import Pipeline

pre = ColumnTransformer([
    ("num", StandardScaler(), ["tenure","MonthlyCharges","avg_monthly","charge_delta"]),
    ("cat", OneHotEncoder(handle_unknown="ignore"),
            ["Contract","InternetService","tenure_bucket"]),
])
pipe = Pipeline([("prep", pre), ("model", lgb.LGBMClassifier(verbose=-1))])
# Now cross_val_score(pipe, ...) refits preprocessing per fold — leak-proof by construction.
```
From this module on: **all preprocessing lives inside a Pipeline. No exceptions.** It's also what you'll deploy in Module 24 — one object, no train/serve skew.

### Exercise
Do a real error-analysis session: 30 worst validation errors, written pattern notes, 2 new features from the patterns, measured before/after. This exercise IS the job.

### Checkpoint ✅
- [ ] I improved a tuned model with features alone
- [ ] All my preprocessing is inside a Pipeline and I can say why
- [ ] I've done one full error-analysis loop

---

## Module 8: The Model Zoo Tour (What Else Exists and When It Wins)

Quick, honest tour — know these, reach for them when their moment comes:

- **k-Nearest Neighbors:** predict from the k most similar training points. No training; slow at prediction; needs scaling. Wins: tiny datasets, recommendation-ish similarity, sanity baseline.
- **Naive Bayes:** probabilistic, assumes feature independence. Wins: text classification baseline, blazing speed, tiny data.
- **SVM:** find the maximum-margin boundary; kernels handle nonlinearity. Wins: small-to-medium high-dimensional data (text, bio). Loses: large datasets (slow), probability quality.
- **Calibrated anything:** if you need real probabilities (risk, pricing), wrap models in `CalibratedClassifierCV` and check with a reliability diagram — boosted trees are often miscalibrated out of the box.
- **Stacking/blending:** feed several models' predictions into a meta-model (`StackingClassifier`). Wins competitions and squeezes final points; costs complexity — use late, not early.

```python
# module8/zoo.py — 15-minute bake-off harness you'll reuse on every new problem
from sklearn.neighbors import KNeighborsClassifier
from sklearn.naive_bayes import GaussianNB
from sklearn.svm import SVC
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, StackingClassifier
from sklearn.model_selection import cross_val_score
import lightgbm as lgb

models = {
    "logreg": make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000)),
    "knn":    make_pipeline(StandardScaler(), KNeighborsClassifier(15)),
    "nb":     GaussianNB(),
    "svm":    make_pipeline(StandardScaler(), SVC(probability=True)),
    "rf":     RandomForestClassifier(300, random_state=0),
    "lgbm":   lgb.LGBMClassifier(verbose=-1, random_state=0),
}
for name, m in models.items():
    s = cross_val_score(m, X_tr, y_tr, cv=5, scoring="roc_auc")
    print(f"{name:<8} {s.mean():.4f} ± {s.std():.4f}")
```
The point isn't that one wins — it's that **you now have a 6-model bake-off you can run on any new dataset in 15 minutes**, and the *pattern* of results (linear ≈ boosting? → problem is linear; huge gap? → interactions matter) diagnoses the problem's nature.

### Checkpoint ✅
- [ ] For each zoo member, I can name one situation where it's the right pick

---

## Module 9: Hyperparameter Tuning & AutoML Reality

### Concept
Tuning = search over model settings, scored by CV. Methods in order of sophistication: grid (exhaustive, wasteful) → random (better coverage per budget — default choice) → Bayesian/successive-halving (**Optuna**, `HalvingRandomSearchCV` — best for expensive models).

```python
# module9/optuna_tune.py     pip install optuna
import optuna, lightgbm as lgb
from sklearn.model_selection import cross_val_score

def objective(trial):
    params = dict(
        num_leaves=trial.suggest_int("num_leaves", 15, 255, log=True),
        learning_rate=trial.suggest_float("learning_rate", 0.005, 0.2, log=True),
        n_estimators=trial.suggest_int("n_estimators", 100, 1500),
        min_child_samples=trial.suggest_int("min_child_samples", 5, 100, log=True),
        subsample=trial.suggest_float("subsample", 0.6, 1.0),
        colsample_bytree=trial.suggest_float("colsample_bytree", 0.6, 1.0),
        verbose=-1, random_state=0)
    return cross_val_score(lgb.LGBMClassifier(**params), X_tr, y_tr,
                           cv=5, scoring="roc_auc").mean()

study = optuna.create_study(direction="maximize")
study.optimize(objective, n_trials=50, show_progress_bar=True)
print(study.best_value, study.best_params)
```

**Reality checks that save you weeks:**
1. Tuning typically buys 1–3% — features and data quality buy 5–20%. Budget accordingly.
2. Never tune on the test set. Tuning on CV, reporting on untouched test — that separation is your integrity.
3. Beware "winner's curse": the best of 500 trials is partly lucky; expect the test score slightly below the best CV score.
4. AutoML (AutoGluon, FLAML, H2O) genuinely works for tabular baselines — run it as a *benchmark to beat*, learn from what it picked, but own your final pipeline (you must debug and maintain it).

### Checkpoint ✅
- [ ] I ran Optuna and can explain why test ≲ best-CV is expected
- [ ] I can defend the sentence "features > tuning" with my own numbers from Module 7

---

# PART 3 — UNSUPERVISED LEARNING

## Module 10: Clustering & Dimensionality Reduction

### Concept
No labels — find structure. Two workhorse families:

**Clustering:** k-Means (fast, assumes roundish clusters, must choose k), DBSCAN (finds arbitrary shapes + flags noise points, no k needed, sensitive to its radius parameter), hierarchical/agglomerative (dendrograms, nested structure), Gaussian mixtures (soft assignments + densities).

**Dimensionality reduction:** PCA (linear projections preserving variance — for compression, decorrelation, plotting), t-SNE/UMAP (nonlinear, for *visualization only* — distances between far-apart blobs are not meaningful; never feed t-SNE output to downstream models as if it preserved global geometry).

### Problem Statement
Segment customers for marketing: cluster your churn dataset's behavioral features, choose k defensibly, and produce named, actionable personas.

### Solution Walkthrough
```python
# module10/segments.py
import pandas as pd, numpy as np, matplotlib.pyplot as plt
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.decomposition import PCA

df = pd.read_parquet("churn_clean.parquet")
feats = df[["tenure", "MonthlyCharges", "TotalCharges"]].copy()
feats["is_monthly"] = (df.Contract == "Month-to-month").astype(int)
X = StandardScaler().fit_transform(feats)      # scaling is MANDATORY for k-means

# Choose k: elbow (inertia) + silhouette, then judgment
for k in range(2, 9):
    km = KMeans(n_clusters=k, n_init=10, random_state=0).fit(X)
    print(f"k={k}  inertia={km.inertia_:.0f}  silhouette={silhouette_score(X, km.labels_):.3f}")

k = 4                                           # suppose elbow+silhouette agree here
km = KMeans(n_clusters=k, n_init=10, random_state=0).fit(X)
df["segment"] = km.labels_

# THE step that makes it useful: profile each cluster in original units
profile = df.groupby("segment").agg(
    n=("customerID", "count"),
    tenure=("tenure", "mean"),
    monthly=("MonthlyCharges", "mean"),
    churn_rate=("Churn", lambda s: (s == "Yes").mean()),
).round(2)
print(profile)
# Now NAME them from the numbers, e.g.:
# 0: "Loyal low-spend"  1: "New high-risk"  2: "Premium stable"  3: "Drifting mid-tenure"

# Visualize via PCA (for the slide deck)
p = PCA(n_components=2).fit_transform(X)
plt.scatter(p[:,0], p[:,1], c=km.labels_, s=6, cmap="tab10")
plt.savefig("segments.png")
```

**Truths about clustering in practice:** there is no "correct" k — there's *useful* k (marketing can act on 4 personas, not 11). Validation is silhouette + stability (re-run with different seeds/subsamples; do the same groups form?) + **the sniff test with domain owners**. A segmentation nobody can name is a segmentation nobody will use.

### Exercise
Run DBSCAN on the same features. Compare: what did it call noise? Did it merge k-means clusters? Write 3 sentences on when you'd prefer each.

### Checkpoint ✅
- [ ] I can choose k with elbow+silhouette+judgment and say why judgment is part of it
- [ ] I profiled clusters in original units and named them

---

## Module 11: Anomaly Detection

### Concept
Find the weird: fraud, defects, intrusions, sensor faults. Approaches by situation:
- **Statistical/rules:** z-scores, IQR fences — when "anomalous" is univariate and known.
- **Isolation Forest:** trees isolate anomalies quickly (few splits to isolate = weird). Strong general default, handles many features.
- **Local Outlier Factor:** density-based; catches points normal globally but odd locally.
- **Autoencoder reconstruction error:** neural net compresses & reconstructs; anomalies reconstruct badly (Module 16 gives you the skill).
- **If you have some labeled anomalies:** it's imbalanced *supervised* learning (Module 22) — usually stronger; use unsupervised methods when labels don't exist yet.

### Problem Statement
Flag anomalous transactions with no labels, tune the alert budget, and design the human review loop.

### Solution Walkthrough
```python
# module11/anomaly.py
import numpy as np, pandas as pd
from sklearn.ensemble import IsolationForest

rng = np.random.default_rng(0)
n = 20000
tx = pd.DataFrame({
    "amount": np.exp(rng.normal(3.4, 1.0, n)),            # log-normal spend
    "hour": rng.integers(0, 24, n),
    "merchant_freq": rng.integers(1, 200, n),             # how often user uses this merchant
    "km_from_home": np.abs(rng.normal(8, 12, n)),
})
# plant 60 frauds: big amounts, 3am, novel merchant, far away
idx = rng.choice(n, 60, replace=False)
tx.loc[idx, ["amount","hour","merchant_freq","km_from_home"]] = \
    np.c_[np.exp(rng.normal(6.2,.4,60)), rng.integers(2,5,60),
          rng.integers(1,3,60), np.abs(rng.normal(500,150,60))]
truth = np.zeros(n, bool); truth[idx] = True

iso = IsolationForest(n_estimators=300, contamination=0.005, random_state=0).fit(tx)
scores = -iso.score_samples(tx)                 # higher = weirder

# Alert budget: review team handles 100/day → threshold = top 100
top = np.argsort(scores)[::-1][:100]
print(f"caught {truth[top].sum()} / 60 planted frauds in a 100-alert budget")
```

**Production design (matters more than the algorithm):**
1. `contamination` / threshold is a **review-capacity decision**, exactly like Module 4's threshold logic.
2. Scores → ranked queue → human review → **verdicts become labels** → within months you can train supervised (better) models. Unsupervised detection is usually a labeling bootstrap, not the end state.
3. Report precision@budget ("of 100 alerts/day, ~35 are real") — that's the business metric.
4. Anomalies drift: retrain on rolling windows; monitor alert-rate stability (Module 25).

### Exercise
Add a seasonal pattern (higher weekend amounts) to normal data and watch Isolation Forest false-alarm on Saturdays. Fix it with a feature (`is_weekend`) rather than a threshold hack — a miniature of real production debugging.

### Checkpoint ✅
- [ ] I can pick a detector from the situation table and justify it
- [ ] I can explain the label-bootstrapping path from unsupervised to supervised

---

# PART 4 — THREE COMPLETE PROJECTS (End-to-End Discipline)

## Module 12: Project 1 — Churn Prediction, For Real This Time

### Problem Statement
*"Retention can call 300 customers a month. Build the system that decides who — and prove its dollar value."* You have all the pieces; this module is about assembling them in professional order and surviving a planted leak.

### The 10-Step Professional Sequence (use this on every project forever)
1. **Frame:** prediction target = "churns within next 30 days," decision = "who gets a call," metric = recall@300 with precision floor, value model = saves × margin − call costs.
2. **Data audit:** Module 2 checklist + a written data dictionary. *Planted trap: this dataset includes `last_call_disposition` — filled in after the retention team calls churners. Find it before it finds you (hint: Module 6's "too good to be true" detector).*
3. **Split first, by time:** train on months 1–9, validate 10–11, test 12. Everything downstream touches only train.
4. **Baselines:** dummy + logistic regression. Write the numbers down — they're your progress meter and your stakeholder anchor.
5. **EDA + features:** Modules 3 & 7. Aggregations per customer (support tickets last 90d, payment failures, usage trend slope).
6. **Model ladder:** LightGBM default → tuned (Optuna, 50 trials). Record CV and validation at every rung.
7. **Error analysis:** 30 worst false negatives (missed churners). At least one new feature from what you find.
8. **Threshold to the business:** top-300 monthly ranking, expected-value calculation per Module 4 Step 3.
9. **Final honest number:** touch the test month once. Report: recall@300, precision@300, AUC, and projected $ value with your assumptions stated.
10. **Package:** single sklearn Pipeline (prep+model) saved with `joblib.dump`, plus `predict.py` that takes a CSV and returns ranked customers. This artifact goes to Module 24 for deployment.

**Deliverable checklist:** data quality report · leak memo (what you found, how) · baseline table · final metrics on test · top-10 drivers (permutation importance) · one-page business memo in plain English. That memo is the difference between a model and a project.

---

## Module 13: Project 2 — Price/Value Regression with Uncertainty

### Problem Statement
*"Estimate used-car sale prices for instant-offer quoting. A quote 15% too high loses money; too low loses sellers. We need predictions AND honest uncertainty."*

### What This Project Teaches Beyond Project 1
- **Skewed targets:** prices are log-normal → train on `np.log1p(price)`, invert with `np.expm1`. Compare MAE both ways; the log-trained model wins on relative error.
- **High-cardinality categoricals:** hundreds of models/trims → target encoding *inside the pipeline/CV* (`category_encoders.TargetEncoder` or sklearn's) — encoded on train folds only, or you've built a leak.
- **Prediction intervals, not just points:** quantile regression gives you "we're 80% sure the price is between X and Y":
```python
import lightgbm as lgb
lo  = lgb.LGBMRegressor(objective="quantile", alpha=0.1, verbose=-1).fit(X_tr, y_tr)
mid = lgb.LGBMRegressor(objective="quantile", alpha=0.5, verbose=-1).fit(X_tr, y_tr)
hi  = lgb.LGBMRegressor(objective="quantile", alpha=0.9, verbose=-1).fit(X_tr, y_tr)
# Validate coverage: ~80% of test prices should land inside [lo, hi].
inside = ((lo.predict(X_te) <= y_te) & (y_te <= hi.predict(X_te))).mean()
print(f"interval coverage: {inside:.1%}  (target 80%)")
```
- **Asymmetric business costs:** overpricing costs 2× underpricing? Quote from the 40th percentile instead of the median, or use a custom loss. Encode the economics into the *operating point*, exactly like Module 4's thresholds.
- **Segment-wise evaluation:** overall MAE hides that you're terrible on luxury cars. Report error by segment (price band, brand, age) — a fairness-and-quality habit that transfers everywhere.

**Data:** any public used-car listings dataset (several on Kaggle/UCI), or scrape-free alternative: simulate from a spec you write — the skills are identical.

**Deliverables:** log-vs-raw comparison table · leak-safe target encoding inside the pipeline · calibrated 80% intervals with measured coverage · per-segment error table · quoting-policy memo connecting percentile choice to the cost asymmetry.

---

## Module 14: Project 3 — Text Classification (Your NLP Gateway)

### Problem Statement
*"Route inbound support emails to billing / technical / account / other — 92%+ accuracy, <50ms per email, explainable."* Classic NLP that still runs the world, and your bridge to Part 5.

### Step-by-Step Build

**Step 1 — Data:** use a public ticket/email classification dataset, or bootstrap: take the 20 Newsgroups dataset (`sklearn.datasets.fetch_20newsgroups`) restricted to 4 categories as a stand-in with identical mechanics.

**Step 2 — The classical pipeline that's embarrassingly hard to beat:**
```python
# module14/text_clf.py
from sklearn.datasets import fetch_20newsgroups
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.metrics import classification_report

cats = ["comp.sys.mac.hardware", "sci.med", "rec.sport.baseball", "talk.politics.misc"]
train = fetch_20newsgroups(subset="train", categories=cats,
                           remove=("headers","footers","quotes"))
test  = fetch_20newsgroups(subset="test",  categories=cats,
                           remove=("headers","footers","quotes"))

clf = Pipeline([
    ("tfidf", TfidfVectorizer(ngram_range=(1,2), min_df=3, max_df=0.9,
                              sublinear_tf=True, stop_words="english")),
    ("lr", LogisticRegression(max_iter=2000, C=2.0)),
]).fit(train.data, train.target)

print(classification_report(test.target, clf.predict(test.data),
                            target_names=test.target_names))
```
TF-IDF = "which words/phrases are distinctive for this document." Logistic regression on top is fast, strong, and **explainable**: the biggest coefficients per class are literally the words that drive the decision — print them and show stakeholders.

**Step 3 — Error analysis on text** (same discipline, new medium): read 30 misclassified emails. You'll find: ambiguous tickets (billing question *about* a technical failure — is your label schema even right?), sarcasm, boilerplate signatures polluting features. Fixes: label-schema revision (talk to the team!), signature stripping, class-specific keyword features.

**Step 4 — Confidence-based routing** (production pattern): `predict_proba` max < 0.6 → route to a human queue instead of guessing. Measure coverage-vs-accuracy tradeoff: "auto-routes 84% of tickets at 96% accuracy; humans handle the uncertain 16%."

**Step 5 — Foreshadowing:** in Module 21 you'll swap TF-IDF for sentence embeddings and for an LLM few-shot classifier, and benchmark all three on THIS dataset. Keep your test split frozen for that bake-off.

**Deliverables:** metrics report · top-15 words per class · error-analysis memo with a label-schema recommendation · confidence-routing curve.

### Part 4 Milestone ✅
Three complete projects with the same skeleton: frame → audit → split honestly → baseline → iterate with error analysis → operating point from business costs → honest final number → packaged pipeline + plain-English memo. **That skeleton is the job.** Deep learning ahead changes the models, never the skeleton.

---

# PART 5 — DEEP LEARNING

## Module 15: Neural Networks from Scratch (No Frameworks, No Mystery)

### Concept
A neural network = layers of linear models with nonlinear "activations" between them. Stacking lets it learn arbitrary functions. Training = your Module 0 gradient descent, with gradients computed layer-by-layer via the chain rule (**backpropagation**).

### Problem Statement
Build a 2-layer network in raw NumPy that learns XOR — the function no linear model can learn — so backprop is forever demystified.

### Solution Walkthrough
```python
# module15/xor_from_scratch.py — a complete neural network in ~30 lines
import numpy as np
rng = np.random.default_rng(0)

X = np.array([[0,0],[0,1],[1,0],[1,1]], float)
y = np.array([[0],[1],[1],[0]], float)          # XOR: not linearly separable

W1 = rng.normal(0, 1, (2, 8)); b1 = np.zeros(8)   # layer 1: 2 → 8
W2 = rng.normal(0, 1, (8, 1)); b2 = np.zeros(1)   # layer 2: 8 → 1
sigmoid = lambda z: 1 / (1 + np.exp(-z))

lr = 0.5
for step in range(5000):
    # ---- forward pass ----
    z1 = X @ W1 + b1;  a1 = np.tanh(z1)           # hidden layer + nonlinearity
    z2 = a1 @ W2 + b2; out = sigmoid(z2)          # output probability
    loss = -np.mean(y*np.log(out) + (1-y)*np.log(1-out))   # cross-entropy

    # ---- backward pass (chain rule, layer by layer) ----
    d_z2 = (out - y) / len(X)                     # ∂loss/∂z2 (neat sigmoid+CE result)
    d_W2 = a1.T @ d_z2;  d_b2 = d_z2.sum(0)
    d_a1 = d_z2 @ W2.T
    d_z1 = d_a1 * (1 - a1**2)                     # tanh derivative
    d_W1 = X.T @ d_z1;   d_b1 = d_z1.sum(0)

    # ---- gradient descent step ----
    W1 -= lr*d_W1; b1 -= lr*d_b1; W2 -= lr*d_W2; b2 -= lr*d_b2
    if step % 1000 == 0: print(f"step {step}: loss {loss:.4f}")

print("predictions:", out.round(3).ravel())       # → ≈ [0, 1, 1, 0] ✓
```
Sit with the backward pass until each line makes sense — it's the chain rule walking backward through the forward pass. **Every framework's `loss.backward()` is this, automated.** Key vocabulary now grounded in code you wrote: forward pass, loss, backprop, learning rate, epoch, activation.

Why nonlinearities matter: delete `np.tanh` (use `a1 = z1`) and watch XOR become unlearnable — stacked linear layers collapse into one linear layer.

### Checkpoint ✅
- [ ] My scratch network solves XOR and I can trace the gradient of one weight by hand
- [ ] I can explain what removing the activation function breaks

---

## Module 16: PyTorch — The Professional Toolkit

### Concept
PyTorch gives you: tensors (GPU-ready NumPy), **autograd** (automatic backprop), `nn.Module` (layer composition), and a training-loop idiom you'll write hundreds of times. Install: `pip install torch` (CPU is fine for this course).

### Problem Statement
Rebuild your churn classifier as a neural net in PyTorch with a proper training loop — early stopping, learning curves, the works — and compare honestly against LightGBM.

### Solution Walkthrough
```python
# module16/torch_churn.py
import torch, torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset
import numpy as np

device = "cuda" if torch.cuda.is_available() else "cpu"

# X_tr, y_tr, X_va, y_va: your scaled numpy arrays from earlier modules
def loader(X, y, bs=256, shuffle=False):
    ds = TensorDataset(torch.tensor(X, dtype=torch.float32),
                       torch.tensor(y.values, dtype=torch.float32).unsqueeze(1))
    return DataLoader(ds, batch_size=bs, shuffle=shuffle)

train_dl, val_dl = loader(X_tr_s, y_tr, shuffle=True), loader(X_va_s, y_va)

model = nn.Sequential(
    nn.Linear(X_tr_s.shape[1], 64), nn.ReLU(), nn.Dropout(0.3),
    nn.Linear(64, 32), nn.ReLU(), nn.Dropout(0.3),
    nn.Linear(32, 1),                       # raw logit; loss applies sigmoid
).to(device)

opt = torch.optim.AdamW(model.parameters(), lr=1e-3, weight_decay=1e-4)
loss_fn = nn.BCEWithLogitsLoss()

best_val, patience, bad_epochs = float("inf"), 8, 0
for epoch in range(200):
    model.train()
    for xb, yb in train_dl:
        xb, yb = xb.to(device), yb.to(device)
        opt.zero_grad()
        loss = loss_fn(model(xb), yb)
        loss.backward()                     # ← Module 15, automated
        opt.step()

    model.eval()
    with torch.no_grad():
        val_loss = np.mean([loss_fn(model(xb.to(device)), yb.to(device)).item()
                            for xb, yb in val_dl])
    print(f"epoch {epoch:3d}  val_loss {val_loss:.4f}")

    if val_loss < best_val - 1e-4:
        best_val, bad_epochs = val_loss, 0
        torch.save(model.state_dict(), "best.pt")     # checkpoint the best
    else:
        bad_epochs += 1
        if bad_epochs >= patience:
            print("early stopping"); break

model.load_state_dict(torch.load("best.pt"))
```
**This loop IS deep learning practice.** Everything else — CNNs, transformers — swaps the `model` and the data loader; the loop barely changes.

The regularization toolkit for nets: dropout, weight decay, early stopping (all above), plus batch norm and data augmentation (next module). Diagnose with the same Module 5 logic: train vs validation curves.

**The honest comparison:** on this tabular data, your net will roughly match — not beat — tuned LightGBM, with more effort. That's the industry-consistent result. **Deep learning earns its complexity on images, text, audio, and sequences** — where we go next.

### Exercise
Overfit on purpose: remove dropout+weight decay, train 200 epochs, plot both curves, watch validation loss U-turn while train loss keeps falling. Now you've *seen* why early stopping exists.

### Checkpoint ✅
- [ ] I can write the PyTorch training loop from memory (really — close the book and try)
- [ ] I can state where deep learning beats gradient boosting and where it doesn't

---

## Module 17: CNNs & Computer Vision (with Transfer Learning)

### Concept
Images are grids where nearby pixels relate. **Convolutions** slide small learnable filters across the image, detecting local patterns (edges → textures → parts → objects as layers stack). Pooling downsamples. This architecture bakes in translation-awareness and parameter sharing — why CNNs crushed hand-crafted vision.

**The single most practical idea in modern DL: transfer learning.** Networks pretrained on millions of images already know edges/textures/shapes. You keep that knowledge and retrain only the final layers on YOUR small dataset. 500 images can reach 90%+ accuracy this way; from scratch you'd need 100×.

### Problem Statement
Classify product photos into 5 categories with only ~500 labeled images — via fine-tuning a pretrained ResNet.

### Solution Walkthrough
```python
# module17/transfer.py    pip install torchvision
import torch, torch.nn as nn
from torchvision import datasets, transforms, models
from torch.utils.data import DataLoader

# Data: folder-per-class layout →  data/train/<class>/*.jpg, data/val/<class>/*.jpg
# (Use your own photos, or a small public set like a 5-class subset of any image dataset)
train_tf = transforms.Compose([
    transforms.RandomResizedCrop(224), transforms.RandomHorizontalFlip(),
    transforms.ColorJitter(0.2, 0.2),                      # augmentation = free data
    transforms.ToTensor(),
    transforms.Normalize([0.485,0.456,0.406], [0.229,0.224,0.225]),  # ImageNet stats
])
val_tf = transforms.Compose([
    transforms.Resize(256), transforms.CenterCrop(224), transforms.ToTensor(),
    transforms.Normalize([0.485,0.456,0.406], [0.229,0.224,0.225]),
])
train_ds = datasets.ImageFolder("data/train", train_tf)
val_ds   = datasets.ImageFolder("data/val", val_tf)

model = models.resnet18(weights="IMAGENET1K_V1")           # pretrained knowledge
for p in model.parameters():
    p.requires_grad = False                                 # freeze the backbone
model.fc = nn.Linear(model.fc.in_features, len(train_ds.classes))  # new head
# → train with the EXACT Module 16 loop (CrossEntropyLoss, only model.fc params in optimizer)
```
Two-phase recipe: (1) train just the head a few epochs; (2) optionally unfreeze the last block with a 10× smaller learning rate for another point or two. Augmentation choices should reflect reality (don't vertically flip street signs).

**Vision task map** (know the names; the transfer recipe generalizes): classification (this) · object detection (boxes — YOLO/Faster R-CNN families) · segmentation (per-pixel — U-Net) · OCR · similarity/embedding search. Modern shortcut: vision-language models (CLIP-style) give zero-shot classification from text labels — benchmark them before labeling anything.

**Evaluation beyond accuracy:** confusion matrix per class; look at misclassified *images* (error analysis, always); test on photos from a different camera/lighting than training — distribution shift is vicious in vision.

### Exercise
Deliberately cause distribution shift: train on bright images, evaluate on dark ones. Measure the drop, then fix with augmentation (`ColorJitter` brightness). This is the vision version of Module 25's drift lesson.

### Checkpoint ✅
- [ ] I fine-tuned a pretrained model on a small dataset and beat 85%+
- [ ] I can explain freezing, heads, and why transfer learning works

---

## Module 18: Sequences, Attention & Transformers

### Concept
Sequences (text, time series, audio) need order-awareness. History in one paragraph: RNNs/LSTMs processed tokens one-by-one, passing a memory forward — worked, but slow and forgetful over long ranges. **Attention** replaced recurrence: every token directly looks at every other token and learns what to attend to. Stack attention layers + feedforward layers = the **Transformer** — the architecture behind BERT, GPT, and the LLM era.

What you need operationally:
- **Tokens:** text is split into subword pieces; models see token IDs.
- **Embeddings:** each token → dense vector; similar meaning ≈ nearby vectors. (This idea powers Module 21 and modern search.)
- **Encoder models (BERT-family):** read whole text bidirectionally → best for classification, extraction, embeddings.
- **Decoder models (GPT-family):** generate left-to-right → best for generation.
- **You will fine-tune and use pretrained transformers; you will (almost) never train one from scratch.** Same transfer-learning economics as Module 17, more extreme.

### Problem Statement
Beat your Module 14 TF-IDF classifier by fine-tuning a small pretrained transformer on the same frozen test split.

### Solution Walkthrough
```python
# module18/finetune.py     pip install transformers datasets accelerate
from transformers import (AutoTokenizer, AutoModelForSequenceClassification,
                          TrainingArguments, Trainer)
from datasets import Dataset
import numpy as np
from sklearn.metrics import accuracy_score, f1_score

MODEL = "distilbert-base-uncased"          # small, fast, plenty for this
tok = AutoTokenizer.from_pretrained(MODEL)

train_ds = Dataset.from_dict({"text": train.data, "label": train.target}) \
    .map(lambda b: tok(b["text"], truncation=True, max_length=256), batched=True)
test_ds  = Dataset.from_dict({"text": test.data, "label": test.target}) \
    .map(lambda b: tok(b["text"], truncation=True, max_length=256), batched=True)

model = AutoModelForSequenceClassification.from_pretrained(MODEL, num_labels=4)

def metrics(p):
    pred = np.argmax(p.predictions, axis=1)
    return {"acc": accuracy_score(p.label_ids, pred),
            "f1": f1_score(p.label_ids, pred, average="macro")}

trainer = Trainer(
    model=model,
    args=TrainingArguments("out", num_train_epochs=3, per_device_train_batch_size=16,
                           eval_strategy="epoch", learning_rate=2e-5,
                           weight_decay=0.01, report_to=[]),
    train_dataset=train_ds, eval_dataset=test_ds, compute_metrics=metrics)
trainer.train()
print(trainer.evaluate())
```
Typical outcome: a few points over TF-IDF — bigger gains the subtler the language (sarcasm, intent, multilingual). Record the three-way scoreboard (TF-IDF / transformer / and in Module 21, LLM few-shot) with cost and latency columns. **Choosing along that frontier is a core professional skill** — the fanciest model is frequently not the right answer at 50ms/email.

**When LLM APIs replace fine-tuning:** <500 labels, fast-changing label schemas, or generation tasks → prompting an LLM wins on time-to-value. Lots of labels + tight latency/cost + stable task → fine-tuned small model wins. You now own both ends of that dial.

### Checkpoint ✅
- [ ] I fine-tuned a transformer and have the honest 3-way comparison table started
- [ ] I can explain encoder vs decoder models and tokens vs embeddings

---

# PART 6 — SPECIALIZED DOMAINS

## Module 19: Time Series Forecasting

### Concept
Time series violates the i.i.d. assumption everything so far leaned on: order matters, and **the future must never inform the past** in your training setup. Non-negotiables:
- **Split by time, always.** Validation = rolling/expanding windows ("backtesting"), never `train_test_split`.
- **Baselines are brutal here:** naive (tomorrow = today) and seasonal-naive (next Monday = last Monday) beat many fancy models. Report MASE (error relative to naive) so you can't fool yourself.
- **Two modeling roads:** classical statistical (ARIMA/ETS/Prophet-style — strong for single clean series) and **ML-as-regression** (build lag/rolling features, use LightGBM — dominant for many related series with covariates, e.g., 5,000 SKUs with promos and prices).

### Problem Statement
Forecast daily demand 14 days ahead for a product with weekly seasonality, a trend, and promotion spikes — the ML way.

### Solution Walkthrough
```python
# module19/forecast.py
import numpy as np, pandas as pd, lightgbm as lgb

# Simulate 2 years of daily demand (swap in your real series)
rng = np.random.default_rng(0)
dates = pd.date_range("2024-07-01", periods=730, freq="D")
trend = np.linspace(100, 140, 730)
weekly = 15*np.sin(2*np.pi*dates.dayofweek/7)
promo = rng.random(730) < 0.05
y = trend + weekly + promo*45 + rng.normal(0, 8, 730)
df = pd.DataFrame({"ds": dates, "y": y, "promo": promo.astype(int)})

# Feature engineering: the heart of ML forecasting
def make_features(d):
    d = d.copy()
    d["dow"] = d.ds.dt.dayofweek
    d["month"] = d.ds.dt.month
    for lag in [1, 7, 14, 28]:
        d[f"lag_{lag}"] = d.y.shift(lag)
    d["roll7_mean"] = d.y.shift(1).rolling(7).mean()    # shift(1) FIRST → no leakage
    d["roll28_mean"] = d.y.shift(1).rolling(28).mean()
    return d.dropna()

feat = make_features(df)
FEATURES = [c for c in feat.columns if c not in ("ds", "y")]

# Backtest: 4 folds, each trains on the past, tests on the next 14 days
folds = [560, 600, 640, 680]
naive_err, model_err = [], []
for cut in folds:
    tr, te = feat.iloc[:cut], feat.iloc[cut:cut+14]
    m = lgb.LGBMRegressor(n_estimators=400, learning_rate=0.05, verbose=-1)
    m.fit(tr[FEATURES], tr.y)
    model_err.append(np.abs(m.predict(te[FEATURES]) - te.y).mean())
    naive_err.append(np.abs(te.y.values - tr.y.iloc[-7:].values[te.dow.values-7]).mean())
print(f"seasonal-naive MAE: {np.mean(naive_err):.2f}")
print(f"model MAE:          {np.mean(model_err):.2f}")
print(f"MASE ≈ {np.mean(model_err)/np.mean(naive_err):.2f}  (<1.0 means you beat naive)")
```

**Multi-step honesty:** predicting 14 days out means lag features beyond `lag_14` aren't available at prediction time for the later horizon days — either build one model per horizon (direct strategy, robust) or feed predictions back in (recursive, error compounds). For many series at once: pool them into one model with series-ID and hierarchy features; that's how modern retail forecasting works.

**Also in the toolbox:** `statsmodels` SARIMAX for interpretable single series; prediction intervals via quantile objectives (Module 13's trick); anomaly-aware preprocessing (a stockout is not demand!).

### Exercise
Break your own backtest: use a random split instead of temporal and report the (inflated, fraudulent) score next to the honest one. Keep that pair of numbers where you can see it.

### Checkpoint ✅
- [ ] My backtesting is temporal and my headline metric is relative to naive
- [ ] I can explain direct vs recursive multi-step and the lag-availability trap

---

## Module 20: Recommender Systems

### Concept
"People who liked X…" Three families:
1. **Collaborative filtering:** learn from the interaction matrix (users × items). Matrix factorization learns a vector per user and item; score = dot product. Needs interaction history; cold-start is its weakness.
2. **Content-based:** recommend items similar (by features/embeddings) to what the user liked. Handles new items; can over-narrow.
3. **Hybrid + ranking:** modern production = candidate generation (fast, recall-oriented: CF + content + popularity) → **ranking model** (your Module 6 LightGBM predicting click/purchase from user/item/context features) → business rules (diversity, freshness, inventory).

### Problem Statement
Build movie recommendations on MovieLens-100k (classic public dataset): matrix factorization via truncated SVD, evaluated the right way (ranking metrics, temporal split).

### Solution Walkthrough
```python
# module20/recs.py
import numpy as np, pandas as pd
from scipy.sparse import csr_matrix
from scipy.sparse.linalg import svds

# MovieLens 100k: userId, movieId, rating, timestamp (grouplens.org)
r = pd.read_csv("ml-100k/u.data", sep="\t", names=["user","item","rating","ts"])

# Temporal split per user: last 5 ratings held out (never random-split interactions!)
r = r.sort_values("ts")
test = r.groupby("user").tail(5)
train = r.drop(test.index)

# Build matrix, factorize
users = {u:i for i,u in enumerate(r.user.unique())}
items = {m:i for i,m in enumerate(r.item.unique())}
M = csr_matrix((train.rating, (train.user.map(users), train.item.map(items))),
               shape=(len(users), len(items)))
U, s, Vt = svds(M.astype(float), k=50)          # 50 latent factors
scores = (U * s) @ Vt                           # predicted affinity for every pair

# Evaluate with ranking metrics: Recall@10
def recall_at_10(u):
    seen = set(train[train.user==u].item.map(items))
    ranked = [i for i in np.argsort(-scores[users[u]]) if i not in seen][:10]
    truth = set(test[test.user==u].item.map(items))
    return len(truth & set(ranked)) / max(len(truth), 1)

sample = r.user.drop_duplicates().sample(300, random_state=0)
print(f"Recall@10: {np.mean([recall_at_10(u) for u in sample]):.3f}")
print(f"popularity baseline: rank by global count and rerun — always compare!")
```

**Evaluation truths:** rating-prediction RMSE is a legacy metric; production cares about **ranking**: Recall@k, Precision@k, NDCG, and coverage/diversity. Popularity is the dummy baseline of recsys — surprisingly hard to beat, always reported. Offline metrics only weakly predict online lift → real systems graduate to A/B tests.

**Cold start playbook:** new user → popularity + onboarding questions + context; new item → content-based from attributes/embeddings until interactions accrue. **Feedback loops:** recommending popular items makes them more popular; log *exposure* (what was shown, not just clicked) and inject exploration.

### Exercise
Build the content-based leg: TF-IDF over movie genres/titles, recommend nearest neighbors to each user's top-rated films, and blend with SVD scores. Measure the blend vs each alone.

### Checkpoint ✅
- [ ] I can draw the candidate-generation → ranking → rules architecture
- [ ] I evaluate with Recall@k against a popularity baseline, on a temporal split

---

## Module 21: Modern NLP — Embeddings, Semantic Search & LLMs in the Stack

### Concept
Three tools cover most industrial NLP today, and you now have the background for all of them:
1. **Sentence embeddings** (`sentence-transformers`): any text → vector; cosine similarity = semantic similarity. Powers search, dedup, clustering of text, and features for classifiers.
2. **Fine-tuned small transformers** (Module 18): stable high-volume tasks.
3. **LLM APIs:** zero/few-shot classification, extraction, summarization, generation — magic time-to-value, costs latency + money per call. (Building *systems* around LLM calls — agents, RAG — is the sibling course you already have.)

### Problem Statement
(a) Semantic search over your support tickets ("find tickets like this one" — beyond keywords). (b) Finish the Module 14/18 bake-off: add an LLM few-shot classifier and produce the final accuracy/latency/cost table.

### Solution Walkthrough
```python
# module21/semantic.py     pip install sentence-transformers
from sentence_transformers import SentenceTransformer
import numpy as np

model = SentenceTransformer("all-MiniLM-L6-v2")   # small, fast, solid
docs = train.data[:2000]                           # your ticket corpus
emb = model.encode(docs, normalize_embeddings=True, show_progress_bar=True)

def search(query, k=5):
    q = model.encode([query], normalize_embeddings=True)
    sims = emb @ q.T                              # cosine (normalized dots)
    for i in np.argsort(-sims[:, 0])[:k]:
        print(f"{sims[i,0]:.3f}  {docs[i][:100]}")

search("my refund never arrived and support won't answer")
# Finds "payment reversal missing", "no response from billing team", ... — no shared keywords needed
```
That's semantic search in 15 lines. At scale you add a vector index (FAISS/Chroma) — mechanics you can now reason about because you know what the vectors are.

**LLM few-shot classifier for the bake-off:** prompt an LLM API with the label set + 3 examples per class, parse the JSON label, run your frozen Module 14 test split. Complete the table:

| Approach | Accuracy | Latency/email | Cost/10k emails | Labels needed |
|---|---|---|---|---|
| TF-IDF + LogReg | ~0.90 | ~1 ms | ~$0 | thousands |
| Fine-tuned DistilBERT | ~0.92–0.94 | ~10 ms | ~$0 (self-hosted) | thousands |
| LLM few-shot | ~0.90–0.95 | ~500–1500 ms | $$ (per call) | ~a dozen |

(Your numbers will vary — that's the point; produce YOUR table.) Reading this table and picking per-constraint is modern NLP judgment: prototypes and low-volume → LLM; stable high-volume → distill down to a small model, often using LLM-generated labels to bootstrap the training set (a now-standard pattern).

**Embeddings as features:** concatenate sentence embeddings with tabular features in your LightGBM — free-text fields ("claim description") become predictive signal inside classic models. Quiet superpower, remember it for the catalog.

### Checkpoint ✅
- [ ] I built semantic search and can explain why it beats keyword search (and when it doesn't)
- [ ] My 3-way bake-off table is complete and I can defend a pick under given constraints

---

## Module 22: Hard-Won Tabular Tricks — Imbalance, Calibration, Interpretation, Fairness

### 22.1 Imbalanced Classification (fraud, defects, rare disease)
In order of what to try:
1. **Right metrics first:** PR-AUC, recall@precision-floor, cost-weighted expected value — never accuracy (Module 4's lesson, sharpened).
2. **Class weights** (`class_weight="balanced"` / `scale_pos_weight`): one-line fix, usually the biggest chunk of the win.
3. **Threshold tuning to business costs:** you already do this (Module 4 Step 3).
4. **Resampling** (undersample majority; SMOTE): sometimes helps, often overrated — apply inside CV folds only (leak alert), and prefer weights first.
5. **More real minority data / better features:** beats all synthetic tricks.

### 22.2 Probability Calibration
"0.8 churn probability" should mean 80 of 100 such customers churn. Check with a reliability curve (`sklearn.calibration.CalibrationDisplay`); fix with `CalibratedClassifierCV` (isotonic/Platt) fit on validation data. Mandatory when probabilities feed pricing, risk, ranking against costs, or expected-value math — i.e., most serious deployments.

### 22.3 Interpretation with SHAP
```python
# pip install shap
import shap
explainer = shap.TreeExplainer(model)          # your LightGBM
sv = explainer(X_te[:500])
shap.plots.beeswarm(sv)                        # global: what drives predictions
shap.plots.waterfall(sv[7])                    # local: why THIS customer scored 0.83
```
Beeswarm answers "what matters overall"; waterfall answers "why this one" — the plot that wins stakeholder trust and satisfies "right to explanation" requirements. Caveats you must say aloud: SHAP explains *the model*, not causality; correlated features share/shuffle credit.

### 22.4 Fairness Sanity Checks (minimum viable responsibility)
Before deploying anything affecting people (lending, hiring, pricing, healthcare):
- **Slice all metrics by protected/relevant groups** — overall AUC hides that recall is 0.81 for one group and 0.55 for another (your Module 13 per-segment habit, now ethical necessity).
- Removing the protected attribute does NOT remove bias — proxies (zip code, names, shopping patterns) carry it. Measure outcomes, don't just delete columns.
- Know the basic criteria (demographic parity, equalized odds, calibration-within-groups), know they can't all hold at once, and know domain law may dictate which matters.
- Document data provenance and known gaps (a model card). If stakes are high, this section is a starting point, not sufficiency — bring in domain/legal review.

### Checkpoint ✅
- [ ] My imbalance playbook starts with metrics and weights, not SMOTE
- [ ] I can produce and read reliability curves, beeswarms, and per-group metric tables

---

# PART 7 — PRODUCTION MLOPS

## Module 23: From Notebook to Pipeline

### Concept
Production ML failure mode #1 is not bad models — it's **irreproducibility and train/serve skew**. Antidotes:
- **One Pipeline object** (Module 7 rule) holding all preprocessing + model → what you validate is byte-identical to what serves.
- **Reproducibility:** pinned environment (`requirements.txt`/lockfile), fixed seeds, versioned data (DVC or immutable snapshots), versioned code (git). Someone must be able to rebuild your model next year.
- **Experiment tracking:** every run's params/metrics/artifacts logged. MLflow in 5 lines:
```python
import mlflow
mlflow.set_experiment("churn")
with mlflow.start_run():
    mlflow.log_params(search.best_params_)
    mlflow.log_metric("test_auc", test_auc)
    mlflow.sklearn.log_model(best_pipe, "model", registered_model_name="churn")
```
- **Project structure that scales:**
```
churn/
  data/{raw,processed}/     # raw is READ-ONLY, forever
  src/{features.py, train.py, evaluate.py, predict.py}
  models/                   # versioned artifacts
  tests/                    # yes, tests for ML code (schema checks, no-leak checks,
  notebooks/                #   "pipeline trains end-to-end on sample data")
```
- **Retraining as a script, not a memory:** `python src/train.py --data data/processed/2026-07.parquet` produces model + metrics + report deterministically. If retraining requires remembering what you did, you don't have a pipeline.

### Exercise
Refactor Project 1 (Module 12) into this structure with MLflow tracking and three pytest tests: schema validation, leak columns absent, end-to-end train on a 500-row sample.

---

## Module 24: Serving Models

### Concept
Match the serving pattern to the need:
| Pattern | Latency | Use case |
|---|---|---|
| **Batch scoring** | hours | Nightly churn scores into a table — *most business ML needs only this* |
| **Online API** | ms | Fraud check at payment time, live pricing |
| **Streaming** | sub-second, continuous | Event-driven scoring (Kafka etc.) |
| **Edge/embedded** | on-device | Mobile, IoT, privacy-constrained |

Start with batch unless the decision truly happens in real time — half of "we need an API" requests are nightly jobs in disguise.

### Step-by-Step: The Online API
```python
# module24/serve.py     pip install fastapi uvicorn
from fastapi import FastAPI
from pydantic import BaseModel, Field
import joblib, pandas as pd

app = FastAPI()
model = joblib.load("models/churn_pipeline.joblib")   # ONE object: prep + model

class Customer(BaseModel):                            # schema validation at the door
    tenure: int = Field(ge=0, le=100)
    MonthlyCharges: float = Field(gt=0)
    TotalCharges: float = Field(ge=0)
    Contract: str
    InternetService: str
    SeniorCitizen: int = Field(ge=0, le=1)

@app.post("/predict")
def predict(c: Customer):
    X = pd.DataFrame([c.model_dump()])
    p = float(model.predict_proba(X)[0, 1])
    return {"churn_probability": round(p, 4),
            "model_version": "churn-2026-07-01"}      # version every response
# run: uvicorn serve:app --port 8000
```
Production hardening checklist: containerize (Docker) · input validation (above — rejects garbage before the model sees it) · log every request/response with model version (you'll need it for Module 25) · latency budget and load test · canary or shadow deployment for new models (serve both, compare, then switch) · rollback = repointing to the previous artifact, rehearsed.

**Batch pattern** (the workhorse): scheduled `predict.py` reads yesterday's data → writes scores table with `model_version` and `scored_at` columns → downstream dashboards/CRM consume the table. Boring, robust, correct for most catalog use cases ahead.

### Exercise
Serve your churn pipeline; send 3 valid requests and 3 invalid ones (negative tenure, missing field, wrong type); confirm the API rejects bad input with clear errors and logs everything.

---

## Module 25: Monitoring, Drift & the Retraining Loop

### Concept
Models decay. The world changes (economics, competitors, seasons), pipelines break silently (a upstream column renamed), and behavior shifts *because* of your model. Monitoring layers, in the order problems appear:

1. **Service health:** uptime, latency, error rate — standard ops.
2. **Input/data drift:** today's feature distributions vs training distributions. A schema change or upstream bug shows up here first. Detect: per-feature PSI/KS tests, missing-rate spikes, category novelty.
3. **Prediction drift:** score distribution shifting (mean churn score creeping up) — early smoke even before labels arrive.
4. **Performance (when labels arrive):** the real metrics, computed on delayed ground truth. **Label delay is the central nuisance** — churn truth arrives 30 days late; fraud truth arrives via chargebacks in 60. Layers 2–3 are your early-warning radar precisely because layer 4 lags.

```python
# module25/drift.py — PSI, the industry-standard drift score
import numpy as np

def psi(expected, actual, bins=10):
    cuts = np.quantile(expected, np.linspace(0, 1, bins + 1))
    cuts[0], cuts[-1] = -np.inf, np.inf
    e = np.histogram(expected, cuts)[0] / len(expected) + 1e-6
    a = np.histogram(actual,  cuts)[0] / len(actual)  + 1e-6
    return float(((a - e) * np.log(a / e)).sum())

# rule of thumb: <0.1 stable · 0.1–0.25 investigate · >0.25 significant drift
for col in ["tenure", "MonthlyCharges"]:
    print(col, round(psi(train_df[col], this_week_df[col]), 3))
```

**The retraining loop that closes the course:**
```
monitor → drift/decay detected → retrain on fresh window (Module 23's script)
→ evaluate vs current champion on held-out recent data (champion/challenger)
→ better? canary deploy → full rollout → keep monitoring
```
Decide retraining cadence by measured decay rate, not vibes: backtest "how much worse is a 3-month-old model on this month's data?" — that number sets your schedule. Log everything (Module 24's request logs) so challenger evaluation is possible at all.

**Feedback loops, the final boss:** your churn model triggers retention calls, which prevent churn, which makes the model look wrong and poisons naive retraining labels. Mitigations: log *interventions* alongside predictions; hold out a small random control group; involve causal thinking when the model changes the world it predicts. Knowing this problem exists puts you ahead of most practitioners.

### Pre-Launch Checklist (print this)
- [ ] Honest offline metrics on a temporally-valid split, vs dummy AND current process
- [ ] Per-segment/per-group metric table reviewed (Module 22.4)
- [ ] Pipeline object serialized; environment pinned; training reproducible by script
- [ ] Input validation at the serving boundary; requests logged with model version
- [ ] Drift monitors (PSI on top features + prediction distribution) with alert thresholds
- [ ] Label-collection path defined; champion/challenger evaluation possible
- [ ] Rollback rehearsed; owner named; retraining cadence justified by decay data

---

# PART 8 — THE USE CASE CATALOG (106 Real-World Builds)

**How to read each entry:** Problem (as a stakeholder states it) → Solution (task type + model family + evaluation) → Build (step sequence; module refs) → ⚠ Gate (evaluation traps and deployment cautions). Difficulty: ★ weekend · ★★ 1–2 weeks · ★★★ serious project.

**How to use it:** every entry is buildable with Parts 1–7 skills. Pick a ★ from your industry first. Note how few distinct *shapes* there are — the meta-patterns section at the end makes that explicit.

---

## Domain A — Marketing & Growth (UC 1–10)

**UC-1. Churn Prediction & Retention Targeting ★★**
Problem: Retention budget sprayed evenly; high-risk customers found after they leave.
Solution: Binary classification (LightGBM) → ranked risk list sized to outreach capacity; drivers via SHAP.
Build: 1) Module 12's 10-step sequence verbatim. 2) Time-based split; 30-day churn window defined precisely. 3) Recall@capacity as headline metric. 4) Control group held out to measure true saves.
⚠ Gate: intervention feedback loop (Module 25) — keep a random holdout or retraining eats itself.

**UC-2. Customer Lifetime Value (CLV) Prediction ★★**
Problem: Acquisition bids treat a $50 customer like a $5,000 one.
Solution: Regression on log-CLV (Module 13 skew trick) or two-stage (P(repeat) × expected value); quantile intervals for risk-aware bidding.
Build: 1) Define horizon (12–24 mo) and label from historical cohorts. 2) Features: early behavior (first 30 days), acquisition channel, basket. 3) Per-segment MAE (Module 13). 4) Feed deciles to ad platforms.
⚠ Gate: survivorship bias — cohorts must include the customers who vanished.

**UC-3. Propensity-to-Convert Lead Scoring ★★**
Problem: Sales chases leads alphabetically.
Solution: Classification → calibrated probability (Module 22.2) so "0.3" is comparable across months; rank + route.
Build: 1) Label = converted within 60d. 2) Split by time AND ensure no post-conversion features (leak trap: "demo_completed"). 3) Calibrate. 4) Route top decile to reps, middle to nurture.
⚠ Gate: leakage from CRM fields updated after conversion — audit field timestamps.

**UC-4. Marketing Mix / Channel Attribution Model ★★★**
Problem: Which channels actually drive revenue vs claim credit?
Solution: Regression with adstock/saturation transforms on spend (media-mix modeling); honest uncertainty; validated on holdout time periods.
Build: 1) Weekly revenue vs channel spends + seasonality controls. 2) Adstock (lagged decay) features. 3) Regularized regression; coefficients = incremental ROI. 4) Validate against any geo-experiments you have.
⚠ Gate: this is causal inference wearing a regression costume — correlated spends confound; recommend experiments where possible; present intervals, not points.

**UC-5. Uplift Modeling (Who Changes Behavior *Because* of the Campaign) ★★★**
Problem: Discounts go to people who'd buy anyway.
Solution: Uplift model — train on a randomized campaign: predict treatment effect per customer (two-model or class-transformation approach); target "persuadables."
Build: 1) You NEED a past randomized send. 2) Two LightGBMs: P(buy|treated), P(buy|control); uplift = difference. 3) Evaluate with Qini/uplift curves, not AUC. 4) Target top-uplift decile next campaign.
⚠ Gate: without randomization this is fiction; validate with a fresh A/B.

**UC-6. Email Send-Time & Subject Optimization ★**
Problem: Blast at 9am Tuesday because someone once said so.
Solution: Per-user open-propensity by hour (classification with hour features) + bandit-style testing for subjects.
Build: 1) Historical send/open logs → per-user-hour model. 2) Score grid of candidate hours per user. 3) Subjects: epsilon-greedy test allocation, not one-shot A/B. 4) Measure lift vs fixed-time control.
⚠ Gate: opens are a noisy proxy (privacy-driven auto-opens) — validate on clicks.

**UC-7. Customer Segmentation for Campaign Design ★**
Problem: One message for everyone.
Solution: k-Means on behavioral features (Module 10 verbatim) → named personas → differentiated campaigns.
Build: 1) RFM + engagement features, scaled. 2) k via elbow+silhouette+actionability. 3) Profile in original units; name segments. 4) Campaign per segment; measure per-segment response.
⚠ Gate: stability check across quarters — segments that reshuffle monthly aren't segments.

**UC-8. Ad Creative Performance Prediction ★★**
Problem: Creative testing burns budget on obvious losers.
Solution: Classification (CTR above median?) from creative features: text embeddings (Module 21) + image embeddings (Module 17 backbone) + format metadata.
Build: 1) Historical creatives + performance. 2) Embed text and image; concatenate with campaign features into LightGBM (Module 21's embeddings-as-features). 3) Pre-screen new creatives; still test survivors. 4) Retrain monthly (creative fatigue = drift).
⚠ Gate: predicts *relative* promise, not absolute CTR — always confirm with live test.

**UC-9. Website Personalization Ranker ★★★**
Problem: Same homepage modules for every visitor.
Solution: Module 20 architecture: candidate modules → ranking model on (user, context, module) features → business rules.
Build: 1) Log exposures + clicks per module. 2) LightGBM ranker (or classifier on click). 3) Serve top-k with diversity rule. 4) A/B against current layout; exploration traffic reserved.
⚠ Gate: position bias in training data (top slots get clicks) — log position, include as feature, or use inverse-propensity weighting.

**UC-10. Social Sentiment & Brand Health Tracker ★**
Problem: Brand perception known only via quarterly surveys.
Solution: Text classification (Module 14/18): sentiment + topic on brand mentions; trend dashboard.
Build: 1) Collect mentions via platform APIs. 2) Fine-tuned small transformer or few-shot LLM (Module 21 bake-off decides). 3) Weekly aggregates with example quotes. 4) Alert on negative-spike anomaly (Module 11).
⚠ Gate: sarcasm and bots; sample-audit classifications monthly; trends > point values.

---

## Domain B — Sales & CRM (UC 11–18)

**UC-11. Deal Win-Probability & Forecast Rollup ★★**
Problem: Pipeline forecast = rep optimism × spreadsheet.
Solution: Classification per open deal (won within stage-appropriate window) with calibrated probabilities; forecast = Σ probabilities × amounts.
Build: 1) Historical deals with stage snapshots (avoid hindsight features!). 2) Features: stage age, activity recency, stakeholder count, amount vs segment norm. 3) Calibration is the whole point (Module 22.2). 4) Backtest forecast vs actuals by quarter.
⚠ Gate: train on stage-time snapshots, not final records — the classic CRM leak.

**UC-12. Next-Best-Action for Reps ★★★**
Problem: Reps guess what to do next on each account.
Solution: Multiclass classification (which action historically preceded advancement, per context) or ranking over action candidates; surfaced in CRM.
Build: 1) Mine action→outcome sequences. 2) Model P(advance | state, action) per action. 3) Recommend argmax with reason codes (SHAP). 4) Measure via staggered rollout.
⚠ Gate: confounding (good reps both pick good actions AND close more) — treat as decision support; validate with experiments.

**UC-13. Sales Email Reply Prediction ★**
Problem: Templates chosen by folklore.
Solution: Classification: P(reply) from email features (embeddings + length + send-time + persona).
Build: 1) Historical outreach logs. 2) Text embeddings + metadata → LightGBM. 3) Score drafts pre-send; surface "what's hurting this email" via SHAP. 4) Confirm with A/B.
⚠ Gate: deliverability confounds (spam filters) — control for domain/warmup.

**UC-14. Territory & Quota Balancing ★★**
Problem: Territories drawn by geography and grievance.
Solution: Regression predicting account potential → optimization (code, not ML) balances predicted potential across reps.
Build: 1) Potential model from firmographics + historical yields on similar accounts. 2) Per-segment error honesty (Module 13). 3) Balancing = integer program/greedy in code. 4) Review with sales ops.
⚠ Gate: potential ≠ guarantee; publish intervals; rebalance annually, not reactively.

**UC-15. Customer Health Score (B2B) ★★**
Problem: CSM "gut feel" health colors.
Solution: Classification (renewal risk) trained on usage telemetry + support + billing signals; score + top-3 drivers per account.
Build: 1) Label = churned/contracted at renewal. 2) Features aggregated over trailing 90d (Module 7 aggregations). 3) SHAP reason codes per account (Module 22.3). 4) CSM playbooks keyed to driver, not just score.
⚠ Gate: small-n problem in B2B (few hundred renewals) — prefer simple models + CV; report uncertainty.

**UC-16. Quote Discount Optimization ★★★**
Problem: Discounts negotiated on vibes; margin leaks.
Solution: P(win | discount, deal context) curve per deal (classification with discount as feature) → expected-margin-maximizing discount recommendation.
Build: 1) Historical quotes with outcomes. 2) Model win-prob as function of discount + context; check monotonicity (constrained LightGBM). 3) Recommend argmax of margin × P(win). 4) Guardrail bands from finance.
⚠ Gate: selection bias (big discounts went to hard deals) — causal caution; bands human-approved; check price-discrimination law with counsel.

**UC-17. Meeting Transcript Insight Miner ★**
Problem: Objections, competitors, feature asks vanish after calls.
Solution: Text extraction/classification over transcripts (Module 21): tag objections, competitor mentions, sentiment; aggregate for enablement.
Build: 1) Transcripts from call recorder. 2) Few-shot LLM or fine-tuned classifier per tag family. 3) Weekly aggregates + trend deltas. 4) Sample-audit tags monthly.
⚠ Gate: recording consent/policy first; PII scrubbing before any external API.

**UC-18. Account Expansion (Upsell) Propensity ★★**
Problem: Expansion revenue found accidentally.
Solution: Classification: P(buys product B | owns A) from usage + firmographics; ranked whitespace list.
Build: 1) Labels from historical cross-sell events. 2) Watch the leak: features must predate the expansion. 3) Rank accounts × products; deliver top-N per rep. 4) Track attach-rate lift vs control.
⚠ Gate: recommend, don't auto-quote; capacity-sized lists (UC-1 logic).

---

## Domain C — Finance, Banking & Risk (UC 19–30)

**UC-19. Credit Default Risk Scoring ★★★**
Problem: Lending decisions need consistent, explainable risk estimates.
Solution: Classification with monotonic constraints (LightGBM `monotone_constraints`: more debt can't lower risk), rigorous calibration, per-group fairness table, full model documentation.
Build: 1) Vintage-based temporal split. 2) Features from bureau + application; leak audit (post-approval fields!). 3) Calibrate; validate by score band. 4) Module 22.4 fairness slices + adverse-action reason codes (SHAP).
⚠ Gate: heavily regulated (fair lending laws, model risk management) — compliance/legal in the loop from day one; interpretability is a legal requirement, not a nicety.

**UC-20. Transaction Fraud Detection ★★★**
Problem: Fraud losses vs false-decline customer rage.
Solution: Imbalanced classification (Module 22.1 playbook) on transaction + behavioral-history features; threshold = review capacity; feedback loop from analyst verdicts.
Build: 1) Labels from chargebacks (60-day delay — Module 25). 2) Features: velocity counts, deviation-from-user-norm (Module 7 aggregations), merchant risk. 3) Precision@alert-budget headline. 4) Analyst verdicts → weekly retraining set.
⚠ Gate: adversarial drift is constant — monitor PSI weekly; latency budget (<100ms) shapes feature choices.

**UC-21. Anti-Money-Laundering Alert Triage ★★★**
Problem: Rule-based AML floods investigators with 95% false positives.
Solution: Classification ranking existing rule alerts by P(true SAR) — ML *prioritizes*, rules still cast the net (regulatory reality).
Build: 1) Historical alerts + investigation outcomes. 2) Network features (counterparty risk, structuring patterns). 3) Rank queue; measure investigator hours per SAR filed. 4) Full audit trail + model documentation.
⚠ Gate: regulators require the rules stay; ML reorders, never suppresses, without validated approval; explainability mandatory.

**UC-22. Loan Prepayment / Early-Closure Prediction ★★**
Problem: Prepayments wreck interest-income forecasts.
Solution: Survival-flavored classification (prepay within horizon) with rate-environment features.
Build: 1) Loan-month panel data. 2) Features: rate gap vs market, loan age, borrower behavior. 3) Temporal backtest across rate regimes. 4) Feed portfolio cash-flow model.
⚠ Gate: regime shifts (rate spikes) break history-trained models — stress-test across past regimes explicitly.

**UC-23. Insurance Claim Severity & Fast-Track ★★**
Problem: All claims through the same slow pipeline.
Solution: Two models: severity regression (log target, quantiles — Module 13) + straight-through-processing classifier (simple, low-risk claims auto-fast-tracked).
Build: 1) Historical claims with final costs. 2) FNOL-time features only (leak trap: adjuster notes come later). 3) Fast-track threshold at precision ≥ 98%. 4) Sample-audit fast-tracked claims monthly.
⚠ Gate: regulatory fairness slices; fraud screen runs before fast-track.

**UC-24. Insurance Fraud Flagging ★★★**
Problem: Fraudulent claims hide in volume.
Solution: UC-20's playbook on claims: imbalanced classification + Isolation Forest for novel patterns (Module 11), union of alerts to investigators.
Build: 1) Confirmed-fraud labels (sparse, delayed). 2) Network features (shared providers/addresses/phones). 3) Precision@investigator-capacity. 4) Verdict feedback loop.
⚠ Gate: accusations are human-only; per-group false-positive audit (Module 22.4).

**UC-25. Cash-Flow Forecasting for Treasury ★★**
Problem: Daily liquidity planning on spreadsheets.
Solution: Module 19 verbatim: per-account daily flows, lag/rolling/calendar features, LightGBM, MASE vs seasonal-naive, quantile bands for stress planning.
Build: 1) 2+ years of flows. 2) Known-future covariates (payroll dates, tax deadlines). 3) Direct multi-horizon models (1–30d). 4) P10/P90 bands drive buffer policy.
⚠ Gate: fat-tail events aren't in the model — bands inform, humans set buffers.

**UC-26. Collections Prioritization ★★**
Problem: Call lists ordered by balance, not recoverability.
Solution: Classification P(cure | contact) or uplift variant (UC-5) → rank by expected recovery × probability.
Build: 1) Historical delinquency + contact outcomes. 2) Uplift framing if past contact was somewhat randomized. 3) Capacity-sized daily lists. 4) Recovery-per-call vs old ordering.
⚠ Gate: collections law constrains contact patterns — rules engine enforces, model only orders.

**UC-27. Customer-Level Price Elasticity ★★★**
Problem: One price for all; margin left on the table or demand destroyed.
Solution: Demand model P(buy | price, context) with monotonic price constraint; simulate revenue vs price; recommend within guardrails.
Build: 1) Requires historical price *variation* (tests, regions, time). 2) Monotonic LightGBM. 3) Simulate revenue curves per segment. 4) A/B validate before rollout.
⚠ Gate: without exogenous price variation this is confounded garbage; legal review (discrimination, dynamic-pricing rules) mandatory.

**UC-28. Invoice Payment-Date Prediction (AR) ★**
Problem: Working-capital planning blind to who pays late.
Solution: Regression (days-to-pay) per invoice from customer payment history + invoice features.
Build: 1) AR ledger history. 2) Customer trailing behavior aggregates. 3) MAE by customer segment. 4) Feed UC-25's cash forecast + prioritize gentle nudges.
⚠ Gate: none major — read-only planning tool; great first finance ML project.

**UC-29. Document Extraction for Loan/KYC Files ★★★**
Problem: Analysts re-key data from statements and IDs.
Solution: OCR + layout-aware extraction (vision + text models, Module 17/18 skills; or document-AI services) with per-field confidence → human verifies low-confidence only.
Build: 1) Field schema + labeled sample (200+ docs). 2) Model or service benchmark; per-field accuracy vs ground truth. 3) Confidence routing (Module 14 Step 4 pattern). 4) Full audit trail.
⚠ Gate: identity data → strict access controls; error rates per field published, not averaged away.

**UC-30. Market/Portfolio Risk Anomaly Monitor ★★**
Problem: Unusual portfolio behavior noticed after the P&L damage.
Solution: Module 11 on portfolio telemetry: exposure drifts, correlation breaks, volume anomalies → ranked morning alerts.
Build: 1) Daily feature vector per book. 2) Isolation Forest + z-score union. 3) Alert budget tuned with risk officers. 4) Verdicts → supervised upgrade path.
⚠ Gate: alerts advise humans; this is surveillance, not trading — keep it out of execution paths.

---

## Domain D — E-commerce & Retail (UC 31–40)

**UC-31. Demand Forecasting per SKU/Store ★★★**
Problem: Stockouts on winners, markdowns on losers.
Solution: Module 19 pooled model: thousands of series, one LightGBM, series-ID + hierarchy + promo/price/calendar features; quantile forecasts feed inventory policy.
Build: 1) 2y sales with promo/price history; stockout-censoring cleanup (a zero-sales stockout day is not zero demand). 2) Backtest MASE by category. 3) P50 for planning, P90 for safety stock. 4) Retrain weekly.
⚠ Gate: censored demand and cannibalization are the two silent killers — handle explicitly.

**UC-32. Product Recommendations ★★★**
Problem: "Customers also bought" is a popularity list.
Solution: Module 20 verbatim: CF + content candidates → LightGBM ranker → diversity/inventory rules.
Build: 1) Interaction logs with exposure logging (position bias!). 2) SVD/implicit-feedback candidates. 3) Ranker on (user, item, context). 4) A/B on revenue-per-session.
⚠ Gate: feedback loop — reserve exploration traffic; cold-start via content leg.

**UC-33. Dynamic Markdown Optimization ★★★**
Problem: End-of-season markdowns are blunt (-30% everything).
Solution: UC-27 elasticity per product × remaining weeks → markdown ladder maximizing sell-through revenue.
Build: 1) Historical markdown responses. 2) Demand model with price + weeks-left. 3) Simulate ladders; recommend per SKU. 4) Pilot in one region vs control.
⚠ Gate: margin floors in code; merchandiser approves ladders.

**UC-34. Search Ranking Improvement ★★★**
Problem: Site search returns keyword matches, not what converts.
Solution: Learning-to-rank: features (text match + embedding similarity (Module 21) + popularity + margin) → LightGBM ranker on click/purchase labels.
Build: 1) Search logs with exposures + outcomes. 2) LGBMRanker with position-bias handling. 3) Offline NDCG on temporal holdout. 4) Interleaved online test.
⚠ Gate: position bias again; guard against margin feature drowning relevance — cap its weight, watch relevance metrics.

**UC-35. Review Fake/Abuse Detection ★★**
Problem: Fake reviews poison ratings and trust.
Solution: Imbalanced classification: text embeddings + behavioral features (reviewer velocity, IP/device patterns, rating deviation).
Build: 1) Labels from past enforcement. 2) Module 22.1 playbook. 3) Precision-first threshold (wrongly deleting real reviews is costly). 4) Appeals loop feeds retraining.
⚠ Gate: enforcement decisions human-reviewed above a severity line; adversaries adapt → monthly drift review.

**UC-36. Size & Fit Recommendation ★★**
Problem: Apparel returns driven by size guessing.
Solution: Classification (right size | customer, product) from purchase-keep/return history + product measurements.
Build: 1) Labels: kept vs returned-for-size. 2) Customer size profile from kept items. 3) "True to size / size up" guidance per product page. 4) Return-rate A/B.
⚠ Gate: cold-start customers get product-level aggregate advice only.

**UC-37. Shelf/Planogram Compliance via Vision ★★★**
Problem: Field audits of store shelves are sparse and slow.
Solution: Module 17 detection: photos → product/facing detection → compare to planogram.
Build: 1) Label 1–2k shelf photos (boxes). 2) Fine-tune a detector (YOLO-family). 3) Compliance score + gap list per photo. 4) Auditor verifies flagged stores.
⚠ Gate: camera/lighting shift (Module 17 exercise!) — augment aggressively; measure per-store-chain accuracy.

**UC-38. Basket Analysis & Cross-Sell Placement ★**
Problem: Merchandising adjacency by intuition.
Solution: Association rules (mlxtend apriori) + embedding co-occurrence; surface high-lift pairs.
Build: 1) Transaction baskets. 2) Support/confidence/lift mining; filter trivial pairs. 3) Validate top rules with a placement test. 4) Quarterly refresh.
⚠ Gate: lift ≠ causality; test before rearranging the store.

**UC-39. Delivery-Time (Promise) Prediction ★★**
Problem: "3–5 business days" is either a lie or sandbagging.
Solution: Quantile regression (Module 13) on order → delivery duration: P80 shown as the promise.
Build: 1) Historical order-to-door durations with carrier/route/weather features. 2) Quantile LightGBM; coverage validation. 3) Per-lane monitoring (Module 25). 4) Promise breach rate as north star.
⚠ Gate: carrier drift is constant — weekly retrain; never show P50 as a promise.

**UC-40. Return Probability at Checkout ★★**
Problem: Serial-return abuse and product-level return drivers invisible.
Solution: Classification P(return | order) — product, customer history, basket signals; informs free-return policy tiers and product-page fixes.
Build: 1) Order→return labels (30–60d delay, Module 25). 2) Segment error honesty. 3) Product-level aggregation → "why returned" mining from reasons text (Module 21). 4) Policy tiers with legal/CS sign-off.
⚠ Gate: customer-level actions (return-policy tightening) are fairness-sensitive — human policy, model informs.

---

## Domain E — Manufacturing & IoT (UC 41–50)

**UC-41. Predictive Maintenance ★★★**
Problem: Machines fail surprise-style; scheduled maintenance over-services healthy units.
Solution: Classification "failure within next N days" from sensor aggregates, or remaining-useful-life regression; alerts sized to maintenance capacity.
Build: 1) Sensor history + failure logs (the hard part — label carefully). 2) Windowed features (rolling stats, spectral features for vibration). 3) **Split by machine** (GroupKFold — Module 4) AND time. 4) Precision@capacity; cost model: false alarm vs missed failure.
⚠ Gate: the group-split rule is everything here — random splits memorize machines and demo-fraud you.

**UC-42. Visual Defect Detection on the Line ★★★**
Problem: Human inspectors miss defects at line speed and drift with fatigue.
Solution: Module 17 transfer learning: camera frames → defect classification/segmentation; threshold tuned to escape-rate target.
Build: 1) Collect + label images (defects are rare — oversample capture around known defects). 2) Fine-tune; heavy augmentation matching line conditions. 3) Recall-first threshold (escapes cost most); flagged units → human station. 4) New-defect-type monitor via reconstruction/embedding anomaly (Module 11).
⚠ Gate: lighting/camera drift; per-shift performance slices; never remove the human station until months of shadow data prove it.

**UC-43. Process Parameter → Quality Prediction ★★**
Problem: Scrap discovered at end-of-line QA, hours after the causal drift.
Solution: Regression (quality metric) from in-process sensor parameters → early warning + SHAP points to the drifting parameter.
Build: 1) Join process telemetry to QA outcomes by batch. 2) LightGBM + SHAP (Module 22.3). 3) Alert when predicted quality crosses spec. 4) Engineers validate causal stories before touching setpoints.
⚠ Gate: correlation ≠ control knob — process changes go through engineering change control.

**UC-44. Energy Consumption Optimization ★★**
Problem: Plant energy bills high; drivers unclear.
Solution: Regression: consumption from production mix + weather + schedule → identifies inefficiency (actual vs predicted gap) and simulates schedule shifts.
Build: 1) Meter data + production logs + weather. 2) Model per meter; residual monitoring = inefficiency detector (Module 11 flavored). 3) What-if simulation for schedule/load shifting. 4) Verified savings tracking.
⚠ Gate: simulation within observed regimes only — extrapolation warnings on.

**UC-45. Supplier Quality Risk Scoring ★★**
Problem: Incoming-inspection resources spread evenly across suppliers.
Solution: Classification P(lot rejected) per incoming lot from supplier history + part + logistics features → inspection intensity tiers.
Build: 1) Inspection outcome history. 2) Trailing supplier aggregates (Module 7). 3) Tiered sampling plan by score. 4) Escape-rate monitoring per tier.
⚠ Gate: keep minimum sampling on "good" suppliers or you blind yourself (exploration!).

**UC-46. Downtime Root-Cause Text Miner ★**
Problem: Years of maintenance logs; recurring causes buried in free text.
Solution: Module 21: embed maintenance notes, cluster (Module 10), label clusters, quantify downtime per cause.
Build: 1) Clean logs; embed. 2) Cluster + LLM-assisted cluster naming. 3) Pareto of downtime hours by cause cluster. 4) Feed top causes to reliability engineering.
⚠ Gate: analytics only; sample-verify cluster assignments before big decisions.

**UC-47. Production Yield Forecasting ★★**
Problem: Weekly output commitments are guesses.
Solution: Module 19 on yield/output per line with planned-maintenance and product-mix covariates.
Build: 1) Historical output + schedules. 2) Known-future covariates (planned mix, maintenance). 3) MASE backtest; quantile bands. 4) S&OP consumes P50/P10.
⚠ Gate: regime changes (new product introductions) → widen bands, flag low-history mixes.

**UC-48. Sensor Fault vs Process Anomaly Disambiguator ★★**
Problem: Anomaly alerts can't tell "sensor died" from "process drifting."
Solution: Two-stage: sensor-health checks (flatline, spikes, cross-sensor consistency — mostly rules + Module 11) before process anomaly scoring.
Build: 1) Per-sensor health features. 2) Isolation Forest per stage. 3) Route: sensor-fault → instrumentation team, process → operations. 4) Track misroute rate.
⚠ Gate: a wrong "sensor fault" call suppresses a real process alarm — bias routing toward process when uncertain.

**UC-49. Digital-Twin-Lite: Throughput What-If ★★★**
Problem: "What if we add a shift on line 3?" answered by argument.
Solution: Regression/simulation hybrid: ML predicts station rates from conditions; discrete-event simulation (code) composes them into throughput scenarios.
Build: 1) Per-station rate models. 2) SimPy-style line simulation consuming model outputs. 3) Scenario reports with uncertainty from model quantiles. 4) Validate vs one historical change.
⚠ Gate: simulation validity limited to observed regimes; label extrapolations loudly.

**UC-50. Acoustic Anomaly Detection ★★★**
Problem: Experienced techs "hear" failing bearings; they retire.
Solution: Audio → spectrogram → Module 17-style CNN (spectrograms are images!) trained on normal sound; anomaly = reconstruction/embedding distance (Module 11 + 15/16 skills).
Build: 1) Record normal operation across conditions. 2) Autoencoder or embedding model on spectrogram patches. 3) Threshold at alert budget; A/B against tech walk-arounds. 4) Confirmed anomalies → supervised classifier over time.
⚠ Gate: background-noise drift (new machinery nearby) — recalibrate normal seasonally.

---

## Domain F — Healthcare & Life Sciences (UC 51–60)

**UC-51. Patient Readmission Risk ★★**
Problem: Preventable readmissions within 30d are costly and signal care gaps.
Solution: Classification on discharge: risk stratification from hospitalization flags + chronic conditions + social factors → intensive follow-up for high-risk.
Build: 1) Readmission label within 30d. 2) Discharge-time features only (leak trap: readmission-related tests). 3) Per-site fairness check (Module 22.4). 4) Pilot 2 sites; measure readmission rate diff vs control.
⚠ Gate: model is *decision support* — care teams own decisions; validate across hospitals (generalization!).

**UC-52. Drug Efficacy Cohort Finder ★★★**
Problem: Trial design needs specific phenotypes; chart review is slow.
Solution: Cohort extraction: rule system (EHR codes) + ML to catch textual variant mentions and automate inclusion/exclusion + uncertainty flagging.
Build: 1) Curate 300 charts: labels = manual cohort status. 2) LightGBM on clinical notes + structured EHR fields (embeddings + tabular). 3) Precision-first (inclusion errors derail trials). 4) Remaining uncertainty → chart review.
⚠ Gate: clinical validation by trial team before rollout; IRB loop.

**UC-53. Hospital No-Show Prediction ★★**
Problem: Clinics waste capacity on no-show appointments.
Solution: Classification per upcoming appointment → reminder timing + overbooking buffer policies.
Build: 1) Appointment-level labels (showed up?). 2) Features: patient history (past no-shows), appointment characteristics, weather. 3) Per-clinic-type error tables (ED vs specialty). 4) A/B reminder strategies.
⚠ Gate: no-show is correlated with access barriers — don't use this to drop poor patients; use to support them.

**UC-54. Lab Test Ordering Appropriateness ★★★**
Problem: Unnecessary labs waste money and expose patients to incidental findings.
Solution: Anomaly-style classification: "is this test order unusual for this patient + problem + recent history?"
Build: 1) Historical orders + chart context. 2) Per-provider order vectors, or Isolation Forest on multi-D order features. 3) Confidence-scaled alerts (high confidence → clinical review, low → suppress noise). 4) Voluntary physician feedback loop.
⚠ Gate: model informs, physicians decide; audit rates per provider; watch for over-suppression.

**UC-55. Sepsis Early Detection ★★★**
Problem: Sepsis kills in hours; early recognition turns outcomes.
Solution: Classification from vital-sign + lab time-series (Module 18 concepts or specialized libraries like `tslearn`); alert escalates fast.
Build: 1) ICU data with sepsis labels (early in course). 2) Rolling 1–4h windows. 3) **Split by patient** to avoid memorizing individuals (GroupKFold). 4) Alert-latency budget <5 min; clinical validation with ICU team.
⚠ Gate: this is directly clinical — requires IRB, clinician oversight, and robust on-call validation before any autonomous routing.

**UC-56. Medical Code Assignment (ICD/CPT) ★★★**
Problem: Billing coders re-assign codes inconsistently; revenue leaks.
Solution: Multi-label classification: clinical notes → suggested diagnosis/procedure codes ranked by confidence; coder confirms top-3.
Build: 1) Historical notes + assigned codes (human-labeled ground truth). 2) Embedding-based multi-label classifier (Module 21). 3) Confidence thresholds per code severity. 4) Appeal/correction → retraining signals.
⚠ Gate: financial stakes — every code suggested must be defensible (explainability); audit reviews quarterly.

**UC-57. Genomics Variant Pathogenicity Prediction ★★★**
Problem: Variants of uncertain significance paralyze clinical interpretation.
Solution: Classification from sequence + structure + conservation + population frequency + literature embedding (transfer learning on BioBERT).
Build: 1) ClinVar database as labels + domain-specific papers embedded. 2) Multi-task learning (benign vs pathogenic vs uncertain). 3) Prediction intervals over confidence. 4) Validation on recent clinical cases.
⚠ Gate: not yet ready for clinical use solo; patient-grade interpretation needs expert review.

**UC-58. Clinical Trial Site Recruitment Forecasting ★★**
Problem: Sites over/underestimate enrollment; trials slip.
Solution: Time-series forecasting (Module 19) per site enrollment velocity.
Build: 1) Past trial enrollment curves. 2) Features: site investigator experience, patient population, screening logs. 3) Weekly updates on ongoing trials. 4) Alerting on pace mismatch vs plan.
⚠ Gate: advisory; trial ops owns decisions; external shocks (new treatments) invalidate history.

**UC-59. Prescription Fill Adherence Prediction ★★**
Problem: Patients don't fill prescriptions; know who won't so you can intervene.
Solution: Classification P(fills within 7d | prescribed) from medication history + insurance + pharmacy visit patterns.
Build: 1) RX-to-fill-date labels. 2) Patient chronicity history + recent fills. 3) Outreach targeting non-fillers (mechanism TBD with patient safety). 4) Medication possession ratio improvements.
⚠ Gate: target individuals carefully (equity!); study unintended consequences (stigma, worse non-adherence from flagging).

**UC-60. Provider Quality Scoring ★★★**
Problem: Patient/insurer choice of provider is blind.
Solution: Regression/calibrated scores on clinical outcomes from provider data (casemix-adjusted; Module 13 fairness): patient mortality/complication rates; publicly reported.
Build: 1) Outcomes per provider (lots of data needed for reliability). 2) Casemix risk-adjustment via matched controls or model-based. 3) Uncertainty intervals per provider (small-n caution). 4) External validation on new data before reporting.
⚠ Gate: Goodhart's law — once providers know they're scored on outcome X, they optimize X perversely; multiple outcomes reduce gaming; beware adverse selection (sick patients seeking top providers, making them look bad).

---

## Catalog Meta-Patterns (Read After 3+ Entries)

Seven recurring skeletons span all 106 use cases:

1. **Binary/multiclass classification ranked by score** (UC-1, 3, 11, 19, 51…) — the backbone. Label carefully; split by time/group; use Module 4's metrics; threshold from business costs; monitor drift (Module 25).

2. **Regression → operate on the prediction** (UC-13, 25, 28, 44…) — quantile flavored for decision-bounds; always validate intervals; clip to observed regimes.

3. **Ranking over candidates** (UC-9, 20, 32, 34…) — Module 20 skeleton: candidates + ranker + rules. Position bias ruins training; position and diversity matter to users.

4. **Time-series forecasting** (UC-25, 31, 47, 58…) — Module 19: temporal split; MASE vs seasonal-naive; quantile bands; external shocks invalidate.

5. **Anomaly / two-stage filtering** (UC-20, 30, 35, 48…) — stage 1 flags candidates (high recall); stage 2 scores/ranks them. Union → human. Feedback loop closes the loop.

6. **Text mining / NLP** (UC-10, 17, 21, 56…) — embeddings + classification or extraction. Module 21 bake-off: TF-IDF vs transformer vs LLM. Cost/latency/accuracy tradeoff wins every time.

7. **Fairness & explainability audits** (UC-19, 27, 53, 60…) — per-group metric tables (Module 22.4); SHAP driver narratives; documentation of known limits. Mandatory in regulated domains; best practice everywhere.

**The meta-move:** when presented with a new use case, pattern-match to one of these skeletons, then ask Module 18's production-hardening questions: What's the cost of wrong? Who's accountable? Is the training data representative? What drifts? What feedback loop closes?

---

# PART 9 — CAPSTONES & THE 14-WEEK PLAN

## Five Capstone Projects

**Capstone 1 — End-to-End Churn Prediction ★★★**
Modules 12 + 23–25: production-grade churn pipeline. Deliverables: trained Pipeline object · frozen test split · MLflow run · driftmonitoring dashboard · one-page business memo. This is your proof of production discipline.

**Capstone 2 — Time-Series Forecasting System ★★★**
Module 19 on a real dataset: daily/weekly aggregates (publicly available retail/energy/traffic data). Backtest across regimes; quantile bands; monthly retraining loop in code; live dashboard mockup.

**Capstone 3 — Text Classification at Scale ★★★**
Module 14/18/21 bake-off baked: TF-IDF + fine-tuned transformer + LLM few-shot, all on the same frozen test split. Complete the comparison table. Bonus: confidence-routing pipeline for low-precision calls to LLM.

**Capstone 4 — Interpretable Model for Regulated Domain ★★★**
Any of UC-19 (credit), UC-51 (readmission), UC-54 (lab testing): constraints + fairness + audit trail + SHAP explanations + model card documentation. This teaches you compliance thinking.

**Capstone 5 — Your Own End-to-End Project ★★★**
Data you have or care about. Frame it yourself; deliver: problem statement → data quality report → 10-step Module 12 sequence → final metrics + deployment design.

**Capstone Rubric:**
- [ ] Works end-to-end on 10 unseen test cases
- [ ] Eval suite with ≥ 50 golden cases; score reported honestly
- [ ] Reproducibility: one `python src/train.py` command works
- [ ] Train vs validation curves plotted; drift monitoring in code
- [ ] Per-group fairness table + error analysis with root causes
- [ ] One-page business memo in plain English

---

## The 14-Week Study Plan

| Week | Do | Ship |
|---|---|---|
| 1 | Modules 0–2 | First Pandas pipeline + EDA function |
| 2 | Modules 3–4 | Churn train/test split honest eval |
| 3 | Module 5–6 | Linear + tree models bake-off |
| 4 | Module 7 | Features beat baseline; error analysis |
| 5 | Modules 8–9 | Zoo tour + first Optuna tuning |
| 6–7 | Modules 10–11 | Clustering + anomaly on real data |
| 8 | Modules 12–13 | Project 1 (churn) complete; Project 2 start |
| 9 | Module 14 | Text classification baseline + 3-way prep |
| 10 | Modules 15–16 | PyTorch loop; overfit on purpose |
| 11 | Modules 17–18 | Transfer + transformer fine-tune |
| 12 | Modules 19–22 | Time series + recommenders + imbalance tricks |
| 13 | Modules 23–24 | Production pipeline + API serving |
| 14 | Module 25 | Monitoring dashboard + retraining loop |
| 15–18 | Capstone | Your chosen end-to-end project |

Then: pick 5 use cases from your industry and build the ★ ones.

---

## Troubleshooting & FAQ

| Problem | Cause | Fix |
|---|---|---|
| Model great in CV, terrible in test | Temporal/group leak | Check if test/train are truly separated; retrain with enforced GroupKFold |
| NaN predictions | Missing feature at inference | Validate inputs before predict; log every NaN |
| Accuracy high, business metric terrible | Wrong metric | Module 4: pick metric from error costs, not habit |
| Production slow | Model or pipeline bottleneck | Profile; batch scoring almost always faster than online |
| Hyperparameter tuning gave 0.1% gain | Tuning past the point of return | Features/data > tuning; do error analysis instead (UC-7 process) |
| Model always predicts the majority class | Extreme imbalance + wrong loss | Module 22.1: class weights, right metric, threshold from costs |
| Same model, different scores on different data | Distribution shift / leap change | Dimensionality reduction + visualization (t-SNE/UMAP on features); identify what changed |
| Stakeholders don't trust the model | Lack of explainability | SHAP per-prediction + per-global; honest error table |
| Model performance drifts after deployment | No drift monitoring in place | Log predictions weekly + p-values on distributions; retrain cadence from decay data |

---

## Glossary (30 Terms That Dominate ML Conversation)

**Backtest** — evaluate on held-out historical data, time-respectingly (future never trains). **Batch** — process many examples at once (faster than one-at-a-time). **Calibration** — predicted probability = empirical rate; check and fix with isotonic/Platt. **Cold start** — model has no history on new users/items; content-based leg bridges. **Cross-validation** — retrain on k folds, aggregate results; honest estimate, not a tuning substitute. **Distribution shift** — input/output distribution changed since training; measure with PSI, mitigate with domain adaptation or retraining. **Embeddings** — vector representation of semantics; similarity = dot product; power modern search/clustering. **Ensemble** — multiple models, combined; boosting is sequential; bagging is parallel (forest). **Fairness** — model has equitable outcomes/treatment across groups; measured, not solved by removing variables. **Generalization** — model's test performance vs training; gap signals overfitting. **Hyperparameter** — settings you choose (lr, n_trees, k) vs parameters (weights) learned; tuned on validation. **Imbalanced** — skewed class ratio; use precision/recall/F1 not accuracy; class-weight and threshold matter. **Interpretability** — "I understand why this prediction happened"; SHAP does this; different from accuracy. **Leakage** — training data contains info unavailable at prediction time; catastrophic. **MAE/RMSE** — regression error; pick from loss structure. **No Free Lunch** — no model beats all others on all tasks; pick per domain. **Overfitting** — train much better than validation; regularize, simplify, or get data. **Precision/Recall** — error-type tradeoff; choose from business cost asymmetry. **Regularization** — penalty on model complexity to prevent overfitting; L1/L2/dropout. **Temporal split** — train on past, validate on middle, test on future; non-negotiable for time-dependent data. **Validation** — held-out data for tuning; test data touched once, blind. **Variance/Bias** — model's flexibility tradeoff; simple→high bias; complex→high variance.

---

## Where to Go Next

- **scikit-learn + XGBoost + LightGBM docs** — your production stack on tabular data
- **PyTorch tutorials** — modern DL baseline
- **Hugging Face transformers** — modern NLP shortcut
- **Papers:** "A Few Useful Things to Know About Machine Learning" (Domingos) · "Rules of Machine Learning" (Google, free) · domain-specific surveys (time series, recsys, fairness)
- **Your own audit trail** — every model you ship that fails teaches more than passing projects

---

*End of course. You started with gradient descent in 10 lines and ended with the architecture and judgment to ship ML systems that work in the real world — where data is messy, business is imperfect, and the model is only one piece of a larger system. The gap between reading and knowing is the projects. Go build. And when you hit a failure, add it to your troubleshooting guide — that document, grown over time, is your actual education.*

