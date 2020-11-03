# MIT License
#
# Copyright (c) 2020 TheCoder777
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.


# load system modules
import io
import re
from datetime import date
from textwrap import wrap

# load external modules
from PyPDF2 import PdfFileWriter, PdfFileReader
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

# load internal modules
from defines import paths
from defines.configs import LINE_DISTANCE


def validate_html_date(html_date):
    """
    Validates a date (yyyy-mm-dd) roughly
    (yes, it's not the greatest date validation ever)
    """
    if re.match(r"[\d][\d][\d][\d]-[\d]?[\d]-[\d]?[\d]", html_date):
        year, month, day = html_date.split("-")
        if not int(year) > 1500:
            return False
        if not int(month) < 12:
            return False
        if not int(day) < 31:
            return False
        # only if nothing returned False
        return True
    else:
        return False


def validate_print_date(html_date):
    # TODO: rename html_date to print_date
    """
    Validates a date for display on the frontend.
    This should be an exact match of dd.mm.yyyy
    """
    return re.match(r"[\d][\d].[\d][\d].[\d][\d][\d][\d]", html_date)


def __convert_to_print_date(html_date):
    return ".".join([html_date.split("-")[2],
                     html_date.split("-")[1],
                     html_date.split("-")[0]])


def reformat_html_to_print(html_date: str) -> str:
    # reformats and validates html and print date
    if validate_html_date(html_date):
        print_date = __convert_to_print_date(html_date)
        if validate_print_date(print_date):
            return print_date
    return "ERROR"  # return empty string if something goes wrong


# we need to implement this slightly different
# def check_start_date(check_date):
#     day, month, year = check_date.split(".")
#     tdate = ".".join([day, month])
#     if tdate == "31.08":
#         return "01.09." + year
#     else:
#         return check_date


def draw(data, packet):
    # generate full name
    fullname = data.get("surname") + ", " + data.get("name")

    c = canvas.Canvas(packet, pagesize=A4)

    # reformat for printing
    start_date = reformat_html_to_print(data.get("start"))
    end_date = reformat_html_to_print(data.get("end"))
    sign_date = reformat_html_to_print(data.get("sign"))
    # TODO: convert first into single variables like nr, year.. then draw
    # Don't ever touch these coordinates I dare you!
    c.drawString(313, 795, fullname)
    c.drawString(386, 778, data.get("unit"))
    c.drawString(231, 748, str(data.get("nr")))
    c.drawString(260, 748, start_date)
    c.drawString(365, 748, end_date)
    c.drawString(530, 748, str(data.get("year")))

    # Betrieblich
    height = 680
    bcontent = data.get("Bcontent").split("\n")
    for cont in bcontent:
        t = c.beginText()
        bcontent = "\n".join(wrap(cont, 80))
        t.setTextOrigin(60, height)
        t.textLines(bcontent)
        c.drawText(t)
        height -= LINE_DISTANCE

    # Schulungen
    height = 515
    scontent = data.get("Scontent").split("\n")
    for scont in scontent:
        st = c.beginText()
        scontent = "\n".join(wrap(scont, 80))
        st.setTextOrigin(60, height)
        st.textLines(scontent)
        c.drawText(st)
        height -= LINE_DISTANCE

    # Berufsschule
    height = 302
    bscontent = data.get("BScontent").split("\n")
    for bscont in bscontent:
        bt = c.beginText()
        bscontent = "\n".join(wrap(bscont, 80))
        bt.setTextOrigin(60, height)
        bt.textLines(bscontent)
        c.drawText(bt)
        height -= LINE_DISTANCE

    c.drawString(95, 148, sign_date)
    c.drawString(260, 148, sign_date)
    c.drawString(430, 148, sign_date)
    c.save()
    return packet


def compile_packet(packet):
    new_pdf = PdfFileReader(packet)
    template = PdfFileReader(open(paths.PDF_TEMPLATE_PATH, "rb"))
    out = PdfFileWriter()
    page = template.getPage(0)
    page.mergePage(new_pdf.getPage(0))
    out.addPage(page)
    out_stream = io.BytesIO()
    out.write(out_stream)
    out_stream.seek(0)
    return out_stream


def create_many(content):
    pages = PdfFileWriter()
    data = {}
    uinput = {}
    for c in content:
        packet = io.BytesIO()
        template = PdfFileReader(open(paths.PDF_TEMPLATE_PATH, "rb"))
        template_page = template.getPage(0)
        uinput["name"] = c[1]
        uinput["surname"] = c[2]
        data["kw"] = c[3]  # only for old draw method, CHANGE THIS SOON!!
        uinput["nr"] = int(c[4]) - 1  # this is because the draw method increases the nr automatically
        uinput["year"] = str(c[5])
        uinput["unit"] = c[6]
        uinput["start_date"] = c[7]
        uinput["end_date"] = c[8]
        uinput["sign_date"] = c[9]
        uinput["Bcontent"] = c[10]
        uinput["Scontent"] = c[11]
        uinput["BScontent"] = c[12]
        packet = draw(data, uinput, packet)
        packet.seek(0)
        new_pdf = PdfFileReader(packet)
        template_page.mergePage(new_pdf.getPage(0))
        pages.addPage(template_page)
        del packet
        del template_page
        del new_pdf

    filename = paths.TMP_PATH + "save.pdf"
    out_stream = open(filename, "wb")
    pages.write(out_stream)
    return filename


def writepdf(data):
    packet = io.BytesIO()
    packet = draw(data, packet)
    packet.seek(0)
    return compile_packet(packet)


def write_many_pdfs():
    packet = io.BytesIO()
    if not "ContentDB" in globals():
        ContentDB = dbhandler.ContentDB(session["user"].id)
    content = ContentDB.get_content()
    return pdfhandler.create_many(content)
