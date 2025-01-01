from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from datetime import datetime

def generate_student_report(student, fees, filename):
    """Generate a PDF report for a student's fee details"""
    doc = SimpleDocTemplate(filename, pagesize=letter)
    styles = getSampleStyleSheet()
    elements = []

    # Title
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        spaceAfter=30
    )
    elements.append(Paragraph('Student Fee Report', title_style))
    elements.append(Spacer(1, 20))

    # Student Details
    student_details = [
        ['Student Details', ''],
        ['Name:', student.name],
        ['Seat Number:', student.seat_number],
        ['Phone Number:', student.phone_number],
        ['Joining Date:', student.joining_date.strftime('%Y-%m-%d')],
        ['Monthly Fee:', f'₹{student.monthly_fee:.2f}']
    ]
    
    student_table = Table(student_details, colWidths=[2*inch, 4*inch])
    student_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 14),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    elements.append(student_table)
    elements.append(Spacer(1, 20))

    # Fee Records
    elements.append(Paragraph('Fee Records', title_style))
    elements.append(Spacer(1, 20))

    if fees:
        fee_data = [['Month', 'Amount', 'Status', 'Payment Date']]
        for fee in fees:
            fee_data.append([
                fee.month.strftime('%B %Y'),
                f'₹{fee.amount:.2f}',
                fee.status.title(),
                fee.payment_date.strftime('%Y-%m-%d') if fee.status == 'paid' else '-'
            ])

        fee_table = Table(fee_data, colWidths=[2*inch, 2*inch, 1.5*inch, 2*inch])
        fee_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ALIGN', (1, 1), (1, -1), 'RIGHT')
        ]))
        elements.append(fee_table)
    else:
        elements.append(Paragraph('No fee records found.', styles['Normal']))

    # Summary
    elements.append(Spacer(1, 20))
    paid_amount = sum(fee.amount for fee in fees if fee.status == 'paid')
    unpaid_amount = sum(fee.amount for fee in fees if fee.status == 'unpaid')
    
    summary_data = [
        ['Summary', ''],
        ['Total Paid:', f'₹{paid_amount:.2f}'],
        ['Total Unpaid:', f'₹{unpaid_amount:.2f}'],
        ['Total Amount:', f'₹{(paid_amount + unpaid_amount):.2f}']
    ]
    
    summary_table = Table(summary_data, colWidths=[2*inch, 4*inch])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 14),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('ALIGN', (1, 1), (1, -1), 'RIGHT')
    ]))
    elements.append(summary_table)

    # Footer
    elements.append(Spacer(1, 20))
    footer_text = f'Generated on: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}'
    elements.append(Paragraph(footer_text, styles['Normal']))

    # Build PDF
    doc.build(elements)

def generate_monthly_report(students, month_date, filename):
    """Generate a PDF report for all students' fees in a specific month"""
    doc = SimpleDocTemplate(filename, pagesize=letter)
    styles = getSampleStyleSheet()
    elements = []

    # Title
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        spaceAfter=30
    )
    elements.append(Paragraph(f'Monthly Fee Report - {month_date.strftime("%B %Y")}', title_style))
    elements.append(Spacer(1, 20))

    # Fee Records
    if students:
        data = [['Seat No.', 'Name', 'Monthly Fee', 'Status', 'Payment Date']]
        total_paid = 0
        total_unpaid = 0

        for student in students:
            fee = next((f for f in student.fees if f.month.strftime('%Y-%m') == month_date.strftime('%Y-%m')), None)
            if fee:
                if fee.status == 'paid':
                    total_paid += fee.amount
                else:
                    total_unpaid += fee.amount
                
                data.append([
                    student.seat_number,
                    student.name,
                    f'₹{student.monthly_fee:.2f}',
                    fee.status.title(),
                    fee.payment_date.strftime('%Y-%m-%d') if fee.status == 'paid' else '-'
                ])
            else:
                data.append([
                    student.seat_number,
                    student.name,
                    f'₹{student.monthly_fee:.2f}',
                    'No Record',
                    '-'
                ])

        table = Table(data, colWidths=[1.2*inch, 2*inch, 1.5*inch, 1.2*inch, 1.5*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ALIGN', (2, 1), (2, -1), 'RIGHT')
        ]))
        elements.append(table)
        elements.append(Spacer(1, 20))

        # Summary
        summary_data = [
            ['Summary', ''],
            ['Total Paid:', f'₹{total_paid:.2f}'],
            ['Total Unpaid:', f'₹{total_unpaid:.2f}'],
            ['Total Expected:', f'₹{(total_paid + total_unpaid):.2f}']
        ]
        
        summary_table = Table(summary_data, colWidths=[2*inch, 4*inch])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 14),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ALIGN', (1, 1), (1, -1), 'RIGHT')
        ]))
        elements.append(summary_table)
    else:
        elements.append(Paragraph('No students found.', styles['Normal']))

    # Footer
    elements.append(Spacer(1, 20))
    footer_text = f'Generated on: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}'
    elements.append(Paragraph(footer_text, styles['Normal']))

    # Build PDF
    doc.build(elements)
