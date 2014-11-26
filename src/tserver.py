#!/usr/bin/env python
# To change this license header, choose License Headers in Project Properties.
# To change this template file, choose Tools | Templates
# and open the template in the editor.

__author__="Rick"
__date__ ="$Nov 24, 2014 9:01:24 AM$"

 
import http.server
import http.server
import cgitb; cgitb.enable()  ## This line enables CGI error reporting
 
server = http.server.HTTPServer
handler = http.server.CGIHTTPRequestHandler
server_address = ("", 8000)
handler.cgi_directories = ["/"]
 
httpd = server(server_address, handler)
httpd.serve_forever()
