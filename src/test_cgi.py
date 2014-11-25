#!/usr/bin/python

# Import modules for CGI handling 
import cgi, cgitb 

# Create instance of FieldStorage 
form = cgi.FieldStorage()
def printform1():
    print "<form action=\"test_cgi.py\" method=\"post\">"
    
    print "<select name=\"dropdown1\">"
    print "<option value=\"Maths\" selected>Maths</option>"
    print "<option value=\"Physics\">Physics</option>"
    print "</select>"
    
    print "<select name=\"dropdown2\">"
    print "<option value=\"Cars\" selected>Cars</option>"
    print "<option value=\"Trucks\">Trucks</option>"
    print "</select>"
    
    print "<input type=\"submit\" value=\"Submit\"/>"
    print "</form>"
    
def getdata1():
    # Get data from fields
    if form.getvalue('dropdown1'):
       return form.getvalue('dropdown1')
    else:
       return "Not entered"
   
def getdata2():
    # Get data from fields
    if form.getvalue('dropdown2'):
       return form.getvalue('dropdown2')
    else:
       return "Not entered"

print "Content-type:text/html\r\n\r\n"
print "<html>"
print "<head>"
print "<title>Dropdown Box - Sixth CGI Program</title>"
print "</head>"
print "<body>"

printform1()

subject1 = getdata1()
subject2 = getdata2()
print "<h2> Selected Subject is {0},{1}</h2>".format(subject1,subject2)
print "</body>"
print "</html>"