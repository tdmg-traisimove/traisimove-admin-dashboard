import secrets
import argparse
import base64
import os
import qrcode
import PIL as pil

def readRandomTokens(filename):
    tokens = []
    with open(filename) as fp:
        tokens = [t.strip() for t in fp.readlines()]
    return tokens

def saveAsQRCode(outdir, token):
    qrcode_data = "nrelopenpath://login_token?token="+token
    qrcode_img = qrcode.make(qrcode_data)
    draw = pil.ImageDraw.Draw(qrcode_img)
    draw.text((55,10), token, fill=0, align="center", anchor="mm")
    qrcode_filename = outdir+"/"+token+".png"
    qrcode_img.save(qrcode_filename)
    return qrcode_filename

if __name__ == '__main__':
    parser = argparse.ArgumentParser(prog="generate_login_qr_codes")

    parser.add_argument("token_file_name")
    parser.add_argument("qr_code_dir")
    args = parser.parse_args()

    tokens = readRandomTokens(args.token_file_name)
    for t in tokens[0:10]:
        print(t)
    os.makedirs(args.qr_code_dir, exist_ok=True)
    for t in tokens:
        saveAsQRCode(args.qr_code_dir, t)    
