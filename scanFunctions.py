import fitz
import pytesseract
import cv2
import re
import requests
import mysql.connector
from mysql.connector import (connection)

punctuations = '''1234567890!()-[]{};:'"\,<>./?@#$%^&*_~‘'''

# ------ save first page of the pdf file
# PARAMS :
#        pdf (string) : filename of the pdf
#        coverImgName (string + ".jpg") : filename of the cover image
def getFirstPage(pdf, coverImgName):
    doc = fitz.open(pdf)
    sampul = doc[0]
    sampul.get_pixmap().save(coverImgName)

# ------ return texts on cover splitted to sections
# sections is text divided by \n\n
# PARAMS :
#        gbr (string) : filename of the cover image
def textOnCover(gbr):
    try:
        img = cv2.imread(gbr)
    except:
        return "cover img file not found"
    result = pytesseract.image_to_string(img)
    sections = re.split("\n\n", result)
    return sections

# ------ return judul, tahun, keanggotaan (sections that contains list of people)
# we can extract the returned by: judul, tahun, keanggotaan = extractInformation(sections)
# PARAMS :
#        sections (python list) : sections returned from textOnCover function above 
def extractInformation(sections):
    judul = ""
    tahun = []
    keanggotaan = []

    if (len(sections[0]) < 12) or (re.search(r"bidang", sections[0], re.IGNORECASE)):
        judul = re.sub(r"\n", " ", sections[2])
    else:
        judul = re.sub(r"\n", " ", sections[1])

    for i in range(len(sections)):
        if tahun == []:
            tahun = re.findall(r"\b\d{4}\b", sections[i])
        if (re.search(r"tim|oleh", sections[i], re.IGNORECASE)):
            if (re.findall(r"\n", sections[i])):
                keanggotaan = re.split("\n", sections[i])
            else:
                keanggotaan = re.split("\n", sections[i+1])
            
    return judul, tahun[0] if tahun!=[] else 0000, keanggotaan

# ------ return list of person (per line)
# PARAMS :
#        keanggotaan (python list) : keanggotaan returned from extractInformation function above
def listOfPersons(keanggotaan):
    person = []
    for line in keanggotaan:
        if (re.search(r"tim|oleh", line, re.IGNORECASE)):
            continue
        person.append(line)
    return person

# ------ return pure names of each person to query like in database
# PARAMS :
#        person (python list) : person returned from listOfPersons function above
def pureNames(person):
    toQuery = []

    for i in range(len(person)):
        tampung = ""
        words = re.split(r" ", person[i])
        for word in words:
            free = ""
            if (len(word) >= 3) and (not (re.search(r"[.]", word))):
                for j in range(len(word)):
                    if word[j] not in punctuations:
                        free += word[j]
                    else:
                        free += " "
                # print("we want to query like for", free)
            free = free.strip()
            if len(free) < 3:
                continue
            if (re.search(r"ketua|anggota|mahasiswa|nidn|nip|stb|nim|research|asean", free, re.IGNORECASE)):
                free = re.sub(r"ketua|anggota|mahasiswa|nidn|nip|stb|nim|research|asean", "", free, flags=re.IGNORECASE)
            if " " in free:
                tampung += free[:free.index(" ")] + " "
            else:
                tampung += free + " "
        toQuery.append(" ".join(tampung.split())) 
    
    return toQuery

def space_to_percent(names):
    toQuery = []

    for name in names:
        toPercent = name.replace(" ", "%%") #double persen karena klo %d atau %s jadinya expect placeholder ki
        toQuery.append("'%%{nama}%%'".format(nama=toPercent))

    return toQuery

def searchInDb(toQuery):
    cnx = mysql.connector.connect(user='root', database='arsip_dosen')
    cursor = cnx.cursor()

    dosen = []
    mahasiswa = []
    header = { "token": "91S0S6NuiA6lsGWism2h3Pn04dN4dPBH" }

    for i in range(len(toQuery)):
        query = "SELECT * FROM dosenn WHERE withGelar LIKE {} LIMIT 1".format(toQuery[i])
        cursor.execute(query, toQuery[i])

        foundDosen = 0

        for (withGelar, Nama, nip, nidn) in cursor:
            foundDosen = 1
            dosen.append({"nama_dosen": withGelar, 
                        "nip": nip})
            
        if (foundDosen != 1): #coba cari di Mhs
            url = "https://customapi.neosia.unhas.ac.id/getNimByNama?nama=" + toQuery[i][1:-1] #hilangkan petik atas di kedua ujung string tolike
            r = requests.post(url, headers=header).json()
            if (r):
                mahasiswa.append({"nama_mahasiswa": r["nama_mahasiswa"].title(), 
                                  "nim": r["nim"]})

    cursor.close()
    cnx.close()

    return dosen, mahasiswa