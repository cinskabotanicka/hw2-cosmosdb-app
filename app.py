import os
import uuid
from flask import Flask, render_template, request, redirect, url_for
from azure.cosmos import CosmosClient, exceptions
from azure.identity import DefaultAzureCredential

app = Flask(__name__)

# --- Cosmos DB connection ---
# Secretless: uses Managed Identity on Azure App Service.
# Locally falls back to Azure CLI credentials (az login).
# COSMOS_KEY is no longer needed in production.
STATIC_BASE_URL = os.environ.get("STATIC_BASE_URL", "/static")

COSMOS_ENDPOINT = os.environ["COSMOS_ENDPOINT"]
DATABASE_NAME = os.environ.get("COSMOS_DATABASE", "myapp-db-hw2")
CONTAINER_NAME = os.environ.get("COSMOS_CONTAINER", "items")

credential = DefaultAzureCredential()
client = CosmosClient(COSMOS_ENDPOINT, credential=credential)
db = client.get_database_client(DATABASE_NAME)
container = db.get_container_client(CONTAINER_NAME)


# --- Routes ---

@app.route("/")
def index():
    """List all tasks, ordered by timestamp descending."""
    items = list(container.query_items(
        query="SELECT * FROM c ORDER BY c._ts DESC",
        enable_cross_partition_query=True
    ))
    return render_template("index.html", tasks=items, static_base_url=STATIC_BASE_URL)


@app.route("/add", methods=["POST"])
def add():
    """Create a new task."""
    title = request.form.get("title", "").strip()
    if not title:
        return redirect(url_for("index"))

    task_id = str(uuid.uuid4())
    container.create_item({
        "id": task_id,
        "title": title,
        "completed": False,
    })
    return redirect(url_for("index"))


@app.route("/toggle/<task_id>")
def toggle(task_id):
    """Toggle completed status of a task."""
    item = container.read_item(item=task_id, partition_key=task_id)
    item["completed"] = not item["completed"]
    container.replace_item(item=task_id, body=item)
    return redirect(url_for("index"))


@app.route("/delete/<task_id>")
def delete(task_id):
    """Delete a task."""
    container.delete_item(item=task_id, partition_key=task_id)
    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(debug=False)
