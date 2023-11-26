from flask import Flask, jsonify, Response, send_file, request
import json
import os
import zipfile
import io

BASE = os.path.dirname(__file__)
PACKAGES = os.path.join(BASE, "packages")

app = Flask(__name__)


def package_path(package: str, *args: str) -> str:
    return os.path.join(PACKAGES, package, *args)


def package_exists(package: str) -> bool:
    return os.path.exists(package_path(package))


def package_meta(package: str) -> dict:
    with open(package_path(package, "meta.json")) as f:
        return json.load(f)


@app.route("/packages/<string:package>/meta")
def _packages_package_meta(package: str):
    if not package_exists(package):
        return jsonify(status="error", error="package not found"), 404
    else:
        return jsonify(package_meta(package))


@app.route("/packages/<string:package>/get")
def _packages_package_get(package: str):
    if not package_exists(package):
        return jsonify(status="error", error="package not found"), 404
    else:
        if version := package_meta(package).get("version"):
            path = package_path(
                package, package_meta(package).get("filename", f"{package}-{version}")
            )
            return Response(open(path, "rb"))
        else:
            return jsonify(status="error", error="invalid package contents")


@app.route("/packages/<string:package>", methods=["POST"])
def _packages_package(package: str):
    zipbundle = request.get_data()
    zf = zipfile.ZipFile(io.BytesIO(zipbundle))
    meta = json.loads(zf.read("meta.json"))
    version = meta.get("version", -1)
    if version < -1:
        return jsonify(status="error", error="invalid version")
    filename = meta.get("filename", f"{package}-{version}")
    if package_exists(package):
        if version <= package_meta(package).get("version"):
            return jsonify(status="error", error="newer version already exists")
        oldmeta = package_meta(package)
    else:
        os.mkdir(package_path(package))
        oldmeta = {"name": package}

    with open(package_path(package, filename), "wb") as f:
        f.write(zf.read(filename))

    for key, val in meta.items():
        oldmeta[key] = val

    with open(package_path(package, "meta.json"), "w") as f:
        json.dump(oldmeta, f)

    zf.close()
    return jsonify(status="success")


@app.route("/")
def _index():
    path = package_path(
        "pmft_installer",
        package_meta("pmft_installer").get("filename", f"pmft_installer"),
    )
    return send_file(path, as_attachment=True, download_name="pmft.py")


if __name__ == "__main__":
    app.run()
