from flask import Flask
from flask import jsonify
from flask import request
from flask_cors import CORS
import requests
import os
import pytesseract
import cv2
import scanFunctions

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = "./tessavedariapi"
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/scan-pdf', methods=['POST', 'GET'])
def scanPenelitian():
    if request.method == "POST":
        file = request.files['filee']
        # if user does not select file, browser also
        # submit an empty part without filename
        if file and allowed_file(file.filename):
            filename = file.filename
            savedfile = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(savedfile)

    coverPictName = "scannow.jpg"

    scanFunctions.getFirstPage(savedfile, coverPictName)
    sections = scanFunctions.textOnCover(coverPictName)
    judul, tahun, keanggotaan = scanFunctions.extractInformation(sections)
    person = scanFunctions.listOfPersons(keanggotaan)
    names = scanFunctions.pureNames(person)
    print(names)
    toQuery = scanFunctions.space_to_percent(names)
    dosen, mahasiswa = scanFunctions.searchInDb(toQuery)

    return jsonify({
        "judul": judul,
        "tahun": tahun,
        "ketua": dosen[0] if len(dosen) > 0 else [],
        "dosen": dosen[1:] if len(dosen) > 1 else [],
        "mahasiswa": mahasiswa if len(mahasiswa) > 0 else []
    })

@app.route('/search-mahasiswa', methods=["POST"])
def searchMhs():
    toQuery = request.form.get("typed")
    toQuery = toQuery.replace(" ", "%%")
    toQuery = "%%" + toQuery + "%%"
    header = { "token": "91S0S6NuiA6lsGWism2h3Pn04dN4dPBH" }

    url = "https://customapi.neosia.unhas.ac.id/getAllNimByKey?key=" + toQuery
    r = requests.post(url, headers=header).json()

    return r

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=133)
