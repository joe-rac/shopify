# 7/8/2025. install with
#           pip install pytz
import io
from PyPDF2 import PdfWriter, PdfReader
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

# TODO in C:\Users\joe1\Dropbox\RAC\notes\rac_ecommerce_notes.txt search for 'python hints' to see good notes/documentation/docs

# 12/1/2019. to get pyPdf2 and reportlab do
# pip install PyPDF2
# pip install reportlab
# here's documentation I used to develop this:
# https://stackoverflow.com/questions/1180115/add-text-to-existing-pdf-using-python
# in particular go to https://www.reportlab.com and look for OPEN SOURCE TOOLKIT and download open source user guide at https://www.reportlab.com/docs/reportlab-userguide.pdf

def convert_text_to_pdf_neaf_invoice(blank_neaf_letterhead_path,text_invoice_path):

    pdf_invoice_path = text_invoice_path.replace('.txt','.pdf')

    packet = io.BytesIO()
    # create a new PDF with Reportlab
    can = canvas.Canvas(packet, pagesize=letter)
    can.setFont("Courier", 12)
    # can.drawString(10, 100, "Hello world")

    with open (text_invoice_path, "r",encoding="utf-8") as myfile:
        lines = myfile.readlines()

    #can.drawString(10, 700, "Hello world")
    offset_vert = 700
    i = 0
    display_line = True
    for line in lines:
        i += 1
        line = line.lstrip().replace('\n','')
        if i == 6:
            can.setFont("Courier", 7)
        if 'SKU Descriptions' in line:
            display_line = False
        if 'BADGE NAMES' in line:
            display_line = True
        if display_line:
            can.drawString(10, offset_vert, line)
            offset_vert -= 10

    can.save()

    #move to the beginning of the StringIO buffer
    packet.seek(0)
    new_pdf = PdfReader(packet)
    # read your existing PDF
    existing_pdf = PdfReader(open(blank_neaf_letterhead_path, "rb"))
    output = PdfWriter()
    # add the "watermark" (which is the new pdf) on the existing page
    page = existing_pdf.pages[0]
    page.merge_page(new_pdf.pages[0])
    output.add_page(page)
    # finally, write "output" to a real file
    outputStream = open(pdf_invoice_path, "wb")
    output.write(outputStream)
    outputStream.close()

    return pdf_invoice_path

def test_convert_text_to_pdf_neaf_invoice():

    # rockland
    blank_neaf_letterhead_path = r"C:\Users\jjmos\Dropbox\RAC_share\NEAF\docs\blank_neaf_letterhead.pdf"
    text_invoice_path =          r"C:\Users\jjmos\OneDrive\Desktop\RAC_DIR\\neaf_output\Antlia_Filter_invoice_2023-03-15_08-10-59.txt"

    # hoboken
    #blank_neaf_letterhead_path = "C:\\Users\\Family\Dropbox\RAC\\NEAF\docs\\blank_neaf_letterhead.pdf"
    #text_invoice_path =          "C:\\Users\\Family\AppData\Local\Temp\\neaf_output\Telescope_Live_invoice_2019-12-01_23-05-39.txt"

    pdf_invoice_path = convert_text_to_pdf_neaf_invoice(blank_neaf_letterhead_path,text_invoice_path)
    print('pdf invoice created at {0}'.format(pdf_invoice_path))


    return

if __name__ == "__main__":
    test_convert_text_to_pdf_neaf_invoice()
