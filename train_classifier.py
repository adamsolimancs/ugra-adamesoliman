import json
import joblib
from pathlib import Path
from sentence_transformers import SentenceTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, f1_score, confusion_matrix

# 1. Prepare sample dataset in a JSONL file: train_data.jsonl
# 2. Load data from JSONL file
texts = []
labels = []
with open("train_data.jsonl", "r") as f:
    for line in f:
        if line.strip():  # skip empty lines if any
            record = json.loads(line)
            texts.append(record["text"])
            labels.append(record["label"])

# 3. Embed sentences into vectors
embedder = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
X_embeddings = embedder.encode(texts, show_progress_bar=False)

# 4. Train/test split
X_train, X_test, y_train, y_test = train_test_split(
    X_embeddings, labels, test_size=0.3, random_state=42
)

# 5. Train logistic regression classifier
clf = LogisticRegression(max_iter=1000)
clf.fit(X_train, y_train)

# 6. Evaluate on test set
y_pred = clf.predict(X_test)
accuracy = accuracy_score(y_test, y_pred)
f1 = f1_score(y_test, y_pred)
conf_mat = confusion_matrix(y_test, y_pred)
print(f"Accuracy: {accuracy:.2f}")
print(f"F1 Score: {f1:.2f}")
print("Confusion Matrix:")
print(conf_mat)

# 7. Save model and embedder pipeline next to this script
model_path = Path(__file__).resolve().parent / "residence_classifier.joblib"
joblib.dump((embedder, clf), model_path)
print(f"Model and embedding pipeline saved to {model_path}")
