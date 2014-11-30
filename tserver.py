#!/usr/bin/env python
# To change this license header, choose License Headers in Project Properties.
# To change this template file, choose Tools | Templates
# and open the template in the editor.

__author__=u"Rick"
__date__ =u"$Nov 24, 2014 9:01:24 AM$"

 
import CGIHTTPServer, SimpleHTTPServer, BaseHTTPServer
import CGIHTTPServer, SimpleHTTPServer, BaseHTTPServer
import cgitb; cgitb.enable()  ## This line enables CGI error reporting
 
server = BaseHTTPServer.HTTPServer
handler = CGIHTTPServer.CGIHTTPRequestHandler
server_address = (u"", 8010)
handler.cgi_directories = [u"/"]
 
httpd = server(server_address, handler)
httpd.serve_forever()
