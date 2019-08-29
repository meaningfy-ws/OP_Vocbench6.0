OP_Vocbench
============
VB_Controller is a tool to run automatically some actions on Vocbench 3.
All is manage using csv template files.

Features
---------
* Written entirely in Python 3
* It allows to create projects automatically using a .csv file
* Upload customs forms
* Load data into a specific projet
* Import ontologies

How to install
--------------
* Install Python 3.4 or newer.
 * Download the source code.
 * Unpack it.
 * Run `setup.py`:
    $ python setup.py install
 * Set your server configuration into the file : setup.cfg
 * Do the following test:

    $ VBController 

To automatically set the server adress and port
-----------------------------------------------

    $ python VBController --setServer=<server_url>:server_port
        or
    $ python VBController -s:<server_url>:server_port

To export data from a specific project
--------------------------------------


To retrieve the configuration information
-----------------------------------------
    $ python VBController -i 

To create projects automatically 
--------------------------------

* Insert the following information in the template file : "Template_Creation_Projects.csv".

| Project name | Prefix |   Namespace   |
| ------------ | ------ | ------------- |
| name of your | prefix | the namespace |
| project      | to use | use           |
       

To add a namespace inside a project 
-----------------------------------
The data has to be placed into the file "Template_Insertion__NameSpace.csv" as shown below :

| Project name | Prefix |   Namespace   |
| ------------ | ------ | ------------- |
| name of your | prefix | the namespace |
| project      | to use | use           |

The first line shall not removed. Then launch the command :

    $ python VBController -s

It will add automaticaly a new Namespace to the designed project.

To change the data folder
-------------------------

The data folder is configured into the file setup.cfg.
It can be manually change inside this file oder using the following command :

    $ python VBController --setDataFd=<newFolderPath>

It creates the folder tree and moves all the files from the previous place

To list the existing projects inside Vocbench
---------------------------------------------
   * To list all the information about projects inside VocBench
   
    $ python VBController -l
    
   * To list only the name of the projects inside VocBench
   
    $ python VBController -n
    
To upload data automatically
----------------------------


The data file has to be placed into the folder defined into setup.cfg under the name DATA_DIR.

To delete automatically a project
---------------------------------

For security reason, this functionnality is not available under VBController.
And also because the deletion needs to be done on VocBench and on GraphDB independently. 
Note
----
A standalone version is also available (build on p2exe). 

Terms and Conditions
--------------------

MIT/X License

Copyright (c) 2018  Publications Office

Permission is hereby granted, free of charge, to any person
obtaining a copy of this software and associated documentation
files (the "Software"), to deal in the Software without
restriction, including without limitation the rights to use,
copy, modify, merge, publish, distribute, sublicense, and/or
sell copies of the Software, and to permit persons to whom the
Software is furnished to do so, subject to the following
conditions:

The above copyright notice and this permission notice shall be
included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY
KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE
WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR
PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR
OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.