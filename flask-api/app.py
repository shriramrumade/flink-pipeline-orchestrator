from flask import Flask, request, jsonify
from db import Base, SessionLocal, Pipeline, engine
import subprocess

app = Flask(__name__)
Base.metadata.create_all(bind=engine)

@app.route("/pipelines", methods=["POST"])
def create_pipeline():
    data = request.get_json()
    session = SessionLocal()
    try:
        pipeline = Pipeline(**data)
        session.add(pipeline)
        session.commit()
        return jsonify({"message": "Pipeline onboarded"}), 201
    except Exception as e:
        session.rollback()
        return jsonify({"error": str(e)}), 400
    finally:
        session.close()

@app.route("/pipelines", methods=["GET"])
def list_pipelines():
    session = SessionLocal()
    pipelines = session.query(Pipeline).all()
    result = [{col.name: getattr(p, col.name) for col in p.__table__.columns} for p in pipelines]
    session.close()
    return jsonify(result)

@app.route("/trigger/<pipeline_id>", methods=["POST"])
def trigger_pipeline(pipeline_id):
    try:
        result = subprocess.run([
            "docker", "exec", "flink-jobmanager",
            "flink", "run", "-py", "/opt/flink_jobs/main.py", "--", pipeline_id
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        if result.returncode != 0:
            return jsonify({"error": "Flink job failed", "stderr": result.stderr.decode()}), 500

        return jsonify({"message": "Triggered", "stdout": result.stdout.decode()}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

