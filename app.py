from flask import Flask, jsonify, request
from flask_cors import CORS
from db import init_db, get_db
from clustering import recluster_notes

app = Flask(__name__)
CORS(app)

init_db()  # initialize database on startup

@app.route("/")
def home():
    return jsonify({"status": "Backend is running"})

# 🔹 GET all notes
@app.route("/notes", methods=["GET"])
def get_notes():
    db = get_db()
    notes = db.execute(
    "SELECT * FROM notes ORDER BY id DESC").fetchall()
    db.close()

    # Convert rows to dicts
    result = [dict(note) for note in notes]
    return jsonify(result)

# 🔹 ADD a new note
@app.route("/notes", methods=["POST"])
def add_note():
    data = request.json
    db = get_db()
    db.execute(
        """
        INSERT INTO notes (id, title, content, category, time, color)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            data["id"],
            data["title"],
            data["content"],
            data["category"],
            data["time"],
            data.get("color", "note-yellow"), # Default color
        )
    )
    db.commit()
    db.close()
    run_clustering_and_update_db()
    
    # Fetch the newly added note to return it (with updated category)
    db = get_db()
    new_note = db.execute(
        "SELECT id, title, content, category, time, color FROM notes WHERE id = ?", 
        (data["id"],)
    ).fetchone()
    db.close()
    
    return jsonify(dict(new_note))

@app.route("/notes/<int:id>", methods=["DELETE"])
def delete_note(id):
    db = get_db()
    db.execute("DELETE FROM notes WHERE id = ?", (id,))
    db.commit()
    db.close()
    run_clustering_and_update_db()
    return jsonify({"success": True})

@app.route("/notes/<int:id>", methods=["PUT"])
def update_note(id):
    data = request.json

    db = get_db()
    db.execute("""
        UPDATE notes
        SET title = ?, content = ?, category = ?, time = ?, color = ?
        WHERE id = ?
    """, (
        data["title"],
        data["content"],
        data["category"],
        data["time"],
        data.get("color", "note-yellow"), # Preserve or update color
        id
    ))
    db.commit()
    db.close()
    run_clustering_and_update_db()
    
    # Fetch the newly updated note to return it (with updated category)
    db = get_db()
    updated_note_row = db.execute(
        "SELECT id, title, content, category, time, color FROM notes WHERE id = ?", 
        (id,)
    ).fetchone()
    db.close()

    return jsonify(dict(updated_note_row))


def run_clustering_and_update_db():
    db = get_db()
    rows = db.execute(
        "SELECT id, title, content FROM notes"
    ).fetchall()

    notes = [dict(row) for row in rows]

    cluster_map = recluster_notes(notes)

    for note_id, category_name in cluster_map.items():
        # category_name is now a string like "Work Project" or "General"
        
        db.execute(
            "UPDATE notes SET category = ? WHERE id = ?",
            (category_name, note_id)
        )

    db.commit()
    db.close()


if __name__ == "__main__":
    app.run(debug=True)
