from flask import Flask
import configs
import time
import mysql.connector
from mysql.connector import errorcode
import numpy as np
import math
import os
import pymysql

from math import pi
def shift(arr, num=1, fill_value=np.nan):
    result = np.empty_like(arr)
    if num > 0:
        result[:num] = fill_value
        result[num:] = arr[:-num]
    elif num < 0:
        result[num:] = fill_value
        result[:num] = arr[-num:]
    else:
        result[:] = arr
    return result

db_user = os.environ.get('CLOUD_SQL_USERNAME')
db_password = os.environ.get('CLOUD_SQL_PASSWORD')
db_connection_name = os.environ.get('CLOUD_SQL_CONNECTION_NAME')

"""
try:
    cnx = mysql.connector.connect(**config)
    print("FUTURES: Bağlantı başarılı")
except mysql.connector.Error as err:
    if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
        print("FUTURES: Something is wrong with your user name or password")
    elif err.errno == errorcode.ER_BAD_DB_ERROR:
        print("FUTURES: Database does not exist")
    else:
        print("FUTURES: ", err)
    """

if os.environ.get('GAE_ENV') == 'standard':
    # If deployed, use the local socket interface for accessing Cloud SQL
    unix_socket = '/cloudsql/{}'.format(db_connection_name)
    cnx = pymysql.connect(user=db_user, password=db_password,
                              unix_socket=unix_socket)
else:
    # If running locally, use the TCP connections instead
    # Set up Cloud SQL Proxy (cloud.google.com/sql/docs/mysql/sql-proxy)
    # so that your application can use 127.0.0.1:3306 to connect to your
    # Cloud SQL instance
    host = '127.0.0.1'
    cnx = pymysql.connect(user=db_user, password=db_password, host=host)

cnx.autocommit = True
cursor = cnx.cursor()



app = Flask(__name__)
@app.route("/")
def home():
    try:
        cursor.execute("USE {}".format(configs.durak_db))
    except mysql.connector.Error as err:
        print("Durak: Database {} does not exists.".format(configs.durak_db))
    durak_text = "<h1>Durak seçiniz</h1>"
    cursor.execute("SELECT * FROM information_schema.tables WHERE table_schema = 'duraklar'")
    records_all = cursor.fetchall()
    duraklar = "<br>".join("<a href=\"durak_no="+x[2]+"\">"+x[2][0:4]+" | "+x[2][4:].replace("_"," ").upper() +"</a>" for x in records_all)
    html = durak_text + duraklar

    return html

@app.route("/durak_no=<durak_no>")
def otobus(durak_no):
    try:
        cursor.execute("USE {}".format(configs.durak_db))
    except mysql.connector.Error as err:
        print("Otobus: Database {} does not exists.".format(configs.durak_db))

    cursor.execute("SELECT `otobus_no` FROM `" + durak_no + "`")
    otobus_nolar = np.array(cursor.fetchall())
    otobus_nolar = otobus_nolar.flatten()

    try:
        cursor.execute("USE {}".format(configs.otobus_db))
    except mysql.connector.Error as err:
        print("Otobus: Database {} does not exists.".format(configs.otobus_db))

    oto_list_array = np.array([])

    for otobusler in otobus_nolar:
        try:
            last_kalan_sure = 999
            last_summe_text = ""
            for max_oto in range(1,50):
                kalan_sure = 999
                exe_text= f"SELECT * FROM `{otobusler}_{max_oto}` WHERE `ulasildi` = '0' and id <= {int(durak_no[1:4])}"
                cursor.execute(exe_text)

                otobus_bilgisi = np.array(cursor.fetchall())
                otobus_bilgisi = np.transpose(otobus_bilgisi)

                otobus_x = otobus_bilgisi[1]
                otobus_y = otobus_bilgisi[2]
                otobus_x_shift = shift(otobus_x,fill_value=0)[1:]
                otobus_y_shift = shift(otobus_y,fill_value=0)[1:]
                otobus_y = otobus_y[1:]
                otobus_x = otobus_x[1:]
                #print(otobus_x)
                #print(otobus_x_shift)

                summe = np.array([])
                for otob_index in range(otobus_y_shift.shape[0]):
                    #enlem x
                    #boylam y
                    lat1 = otobus_x[otob_index]
                    long1 = otobus_y[otob_index]
                    lat2 = otobus_x_shift[otob_index]
                    long2 = otobus_y_shift[otob_index]

                    d = math.acos(math.sin(pi * lat1 / 180.0) * math.sin(pi * lat2 / 180.0) + math.cos(pi * lat1 / 180.0) * math.cos(pi * lat2 / 180.0) * math.cos(pi * long2 / 180.0 - pi * long1 / 180.0)) * 6371
                    # https://qastack.info.tr/programming/13026675/calculating-distance-between-two-points-latitude-longitude
                    summe = np.append(summe,d)
                summe = np.sum(summe)
                otobus_hiz = otobus_bilgisi[4][0]
                if otobus_hiz < 10:
                    otobus_hiz = 10

                if summe == 0:
                    exe_text = f"SELECT * FROM `{otobusler}_{max_oto}` WHERE `id` =  {int(durak_no[1:4])} or `id` = 0"
                    cursor.execute(exe_text)
                    sifir_oto = np.transpose(np.array(cursor.fetchall()))

                    lat1 =sifir_oto[1][0]
                    long1 = sifir_oto[2][0]

                    lat2 = sifir_oto[1][1]
                    long2 = sifir_oto[2][1]

                    d = math.acos(math.sin(pi * lat1 / 180.0) * math.sin(pi * lat2 / 180.0) + math.cos(pi * lat1 / 180.0) * math.cos(pi * lat2 / 180.0) * math.cos(pi * long2 / 180.0 - pi * long1 / 180.0)) * 6371
                    if d < 0.035:
                        kalan_sure_text = "Geldi"
                    else:
                        kalan_sure_text = "Geçti"
                else:
                    kalan_sure = summe/otobus_hiz
                    kalan_saat = int(kalan_sure)
                    kalan_dakika = (kalan_sure % 1) * 60

                    kalan_saniye = (kalan_dakika % 1) * 60
                    if kalan_saat == 0:
                        kalan_saat_text =""
                    else:
                        kalan_saat_text = "{} st ".format(int(kalan_saat))

                    if kalan_dakika == 0:
                        kalan_dakika_text =""
                    else:
                        kalan_dakika_text = "{} dk ".format(int(kalan_dakika))

                    if kalan_saniye == 0:
                        kalan_saniye_text = ""
                    else:
                        kalan_saniye_text = "{} sn".format(int(kalan_saniye))

                    kalan_sure_text = kalan_saat_text+kalan_dakika_text+kalan_saniye_text

                if kalan_sure < last_kalan_sure or summe == 0 or last_summe_text == "Geçti":
                    if max_oto != 1 or last_summe_text == "Geçti":
                        oto_list_array = oto_list_array[:-1]
                    oto_list_array = np.append(oto_list_array, f"{otobusler} | {kalan_sure_text}")
                last_kalan_sure = kalan_sure
                print(last_summe_text)
                last_summe_text = kalan_sure_text
                print(otobusler,kalan_sure_text, summe, otobus_hiz)


        except Exception as a:
            print(a)
    print(oto_list_array)
    html_head = "Durak numarası: {}<br>Durak adı: {}".format(durak_no[:4],durak_no[4:].replace("_"," ").upper())
    html_oto_list = "<br>" + "<br>".join(x for x in oto_list_array)
    html = html_head + html_oto_list
    return html

if __name__ == "__main__":
    # This is used when running locally only. When deploying to Google App
    # Engine, a webserver process such as Gunicorn will serve the app.
    app.run(host='127.0.0.1', port=8080, debug=True)
    # [END gae_flex_quickstart]
