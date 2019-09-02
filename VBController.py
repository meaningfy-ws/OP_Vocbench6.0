#! /usr/bin/env python3
# coding: utf-8

import sys, getopt
import requests
import csv
import codecs
import json
import re
import os
import logging
import shutil

from urllib3.exceptions import MaxRetryError, ConnectTimeoutError
from requests.exceptions import ReadTimeout
from requests.exceptions import ConnectTimeout

#Global Variables
server = ""
port = ""
dataFile = ""
data_folder = ""
serverInfo = ""
files_folder = ""
ontologies_folder = ""
form_folder = ""
log_folder = ""
tmp_folder = ""
templates_folder = ""
session = requests.Session() # Connexion open with Vocbench
logger = ""
user = ""
password = ""

# Customs forms
custom_forms = {'reifiednotes1' : """
                        prefix  xsd:    <http://www.w3.org/2001/XMLSchema#>
                        prefix  rdf:    <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
                        prefix  dct:    <http://purl.org/dc/terms/>
                        prefix  coda:   <http://art.uniroma2.it/coda/contracts/>
                        prefix  codaImpl:   <http://art.uniroma2.it/coda/converters/>
                        prefix euvoc: <http://publications.europa.eu/ontology/euvoc#>
            
                        rule it.uniroma2.art.semanticturkey.customform.form.reifiednote.srcap id:reifiednote {
                        nodes = {
                            reifNoteId uri(coda:randIdGen("note", {})) .
                            noteLang literal userPrompt/lang .
                            noteLit literal(coda:langString($noteLang)) userPrompt/note .
                            source literal userPrompt/source .
                        }
                        graph = {
                            $reifNoteId a euvoc:XlNote .
                            $reifNoteId rdf:value $noteLit .
                            OPTIONAL { $reifNoteId dct:source $source . }
                        }}"""}

#################################################
# Set the configuration variables
#################################################
def set_configuration():

    global files_folder
    global data_folder
    global form_folder
    global log_folder
    global tmp_folder
    global templates_folder
    global ontologies_folder
    global session
    global server
    global port
    global user
    global password

    with open("./setup.cfg", "r", encoding='utf8') as f:
        lines = f.readlines()

    #Set the configurations values
    for line in lines:
        tmp, value = line.split("=")
        if ("Server" in tmp):
            server = value.strip()
        elif ("Port" in tmp):
            port = value.strip()
        elif ("User" in tmp):
            user = value.strip()
        elif ("Password" in tmp):
            password = value.strip()
        elif("FILES_DIR" in tmp):
            files_folder = value.strip()
        elif("ONTOLOGY_DIR" in tmp):
            ontologies_folder = value.strip()
        elif ("FORM_DIR" in tmp):
            form_folder = value.strip()
        elif ("LOG_DIR" in tmp):
            log_folder = value.strip()
        elif ("TMP_DIR" in tmp):
            tmp_folder = value.strip()
        elif ("DATA_DIR" in tmp):
            data_folder = value.strip()
        elif ("TEMPLATES_DIR" in tmp):
            templates_folder = value.strip()
    return

####################################################################
# Connection to VocBench using the data from the configuration file
####################################################################
def connection():

    global session
    global server
    global port
    global logger
    global user
    global password

    if (server=="") or (port==""):
        logger.error("Wrong configuration of the server")
        sys.exit()

    if (user == "" or user == None) or (password == "" or password == None)\
            or (port == "" or port == None) or (server == "" or server == None):
        logger.error("Connexion not available - see configuration file")
        return

    payload = {'email' : user, 'password' : password, '_spring_security_remember_me':'false'}
    server = server.rstrip("/")
    port = port.lstrip(":")
    try:
        r = session.post(server + ":" + port + "/semanticturkey/it.uniroma2.art.semanticturkey/st-core-services/Auth/login?",
                   params = payload, timeout = 1)
    except (MaxRetryError, ConnectTimeoutError, ConnectTimeout, ReadTimeout):
        logger.error("No server connexion")
        sys.exit()

    if (r.status_code >300) or (r.status_code<200):
        logger.error(r.text)
        sys.exit()
    else:
        logger.info("Connection ok")
    
    return json.loads(r.content)

###################################################################################################
# Creation of projects into VocBench using the data from the file : "Template_Creation_Projects.csv"
# and automatic addition of the Namespaces (if specified)
###################################################################################################
def project_creation():

    global session
    global dataFile
    global files_folder
    global logger
    global custom_forms
    
    pathF = ""
    connection()

    if (dataFile == ""):
        if (os.path.exists(os.path.join(files_folder, "Template_Creation_Projects.csv"))):
            pathF =os.path.join(files_folder, "Template_Creation_Projects.csv")
        else:
            logger.error("The data file is not declared or not find")
            sys.exit()
    elif (os.path.exists(dataFile)):
        pathF = dataFile
    else:
        logger.error("The data file is not declared or not find")
        sys.exit()

    if (pathF != ""):
        with codecs.open(pathF, encoding='utf8') as f:
            reader = csv.reader(f, delimiter=';')
            first = True
            for row in reader:
                if not first:
                    if _check_if_Project(row[0]):
                        logger.error('the project "'+ row[0] + '" already exists in VocBench')
                        continue
                    
                    base_uri = ""
                    if (len(row[1].strip()) > 1):
                        base_uri = row[1]
                    else:
                        base_uri = get_base_uri_from_file(row[15])
            
                    payload = {'extensionPointID': 'it.uniroma2.art.semanticturkey.extension.extpts.repositoryimplconfigurer.RepositoryImplConfigurer'}
                    r = session.get(server + ":" + port + "/semanticturkey/it.uniroma2.art.semanticturkey/st-core-services/Extensions/getExtensions?",
                        params=payload)
                    logger.info(r.content)
                    
                    payload = {'extensionPoint': 'it.uniroma2.art.semanticturkey.plugin.extpts.URIGenerator'}
                    r = session.get(server + ":" + port + "/semanticturkey/it.uniroma2.art.semanticturkey/st-core-services/Plugins/getAvailablePlugins?",
                        params=payload)
                    logger.info(r.content)

                    payload = {'extensionPoint': 'it.uniroma2.art.semanticturkey.plugin.extpts.RenderingEngine'}
                    r = session.get(server + ":" + port + "/semanticturkey/it.uniroma2.art.semanticturkey/st-core-services/Plugins/getAvailablePlugins?",
                        params=payload)
                    logger.info(r.content)

                    payload = {'factoryID': 'it.uniroma2.art.semanticturkey.plugin.impls.urigen.CODAURIGeneratorFactory'}
                    r = session.get(server + ":" + port + "/semanticturkey/it.uniroma2.art.semanticturkey/st-core-services/Plugins/getPluginConfigurations?",
                        params=payload)
                    logger.info(r.content)
                    
                    payload = {'factoryID': 'it.uniroma2.art.semanticturkey.plugin.impls.rendering.OntoLexLemonRenderingEngineFactory'}
                    r = session.get(server + ":" + port + "/semanticturkey/it.uniroma2.art.semanticturkey/st-core-services/Plugins/getPluginConfigurations?",
                        params=payload)
                    logger.info(r.content)
                    
                    payload = {'properties': 'remote_configs'}
                    r = session.get(server + ":" + port + "/semanticturkey/it.uniroma2.art.semanticturkey/st-core-services/PreferencesSettings/getSystemSettings?",
                        params=payload)
                    logger.info(r.content)
                    
                    payload = {'consumer':'SYSTEM', 'projectName' : row[0], 'baseURI' : base_uri, 'model' : row[2],
                   'lexicalizationModel' : row[3], 'historyEnabled' : row[4], 'validationEnabled' : row[5], 'blacklistingEnabled' : row[6], 'repositoryAccess': row[7],
                   'coreRepoID' : row[9], 'supportRepoID': row[10] , 'coreRepoSailConfigurerSpecification':row[11],
                    'supportRepoSailConfigurerSpecification':row[12], 'creationDateProperty': row[13], 'modificationDateProperty': row[14]}
                    
                    if (base_uri == ""):
                        logger.error("Error : the base URI of the project is not defined")
                        sys.exit()
 
                    r = session.post(server + ":" + port + "/semanticturkey/it.uniroma2.art.semanticturkey/st-core-services/Projects/createProject?",
                            params = payload)
                    logger.info(r.content)
                    
                    data_path = os.path.join(data_folder, row[14])
                    # Add the data if they are available
                    if(os.path.exists(data_path)):
                        data_upload(row[14], row[0], base_uri)

                    if (_check_if_Project(row[0])):
                        logger.info('The project "' + row[0]+ '" is well created')
                    else:
                        logger.error("The creation of the project " + row[0] + " has failed")
                    
                    if (row[15] != ""):
                        if row[15] in custom_forms:
                            createForm(row[0], row[15])
                
                    if (row[16].lower() == 'yes'):
                        importOntology(row[0])
                        
                    validate_all(row[0])
                    
                    close_project(row[0])
                
                first = False
    return

##############################################################
# List all the projects inside the system
###############################################################
def get_base_uri_from_file(file_name):
    global logger
    base_uri = ""
    if(file_type(file_name) == 'ttl'):
        n_spaces = parse_nspace_ttl(file_name)
        base_uri = n_spaces["  "]
    elif (file_type(file_name) == 'rdf'):
        n_spaces = parse_nspace_rdf(file_name)
        base_uri = n_spaces["  "]
    else:
        logger.error("The file type of the file" + file_name + " is not identified")
    return base_uri

##############################################################
# List all the projects inside the system
###############################################################
def parse_nspace_nt(file_name):
    global data_folder
    pathF = data_folder + "/" + file_name
    n_spaces = {}
    final = ""
    with open(pathF, encoding='utf8') as f:
        lines = f.readlines()
    
    for line in lines:
        l = line.strip()
        if (len(l) == 0):
            continue
        if l[0] == '#':
            continue
        final = final + "\n" + line
    
    declaration = re.findall("@prefix.*>[\s\n]*?\.", final)
    
    for d in declaration:
        prefix = d.split(":", 1)[0]
        prefix = re.sub("@prefix", "", prefix)
        name_space = d.split(":", 1)[1]
        name_space = name_space.strip(".")
        name_space = name_space.strip()
        name_space = name_space.strip("<")
        name_space = name_space.strip(">")
        if len(str(prefix).strip()) == 0:
            n_spaces["  "] = name_space
        else:
            n_spaces[prefix] = name_space
    for n, v in n_spaces.items():
        print(n + ":" + v)
    return n_spaces

##############################################################
# List all the projects inside the system
###############################################################
def list_of_project(only_title):

    connection()
    global logger
    global server
    global port
    res = ""
    payload = {'consumer' : 'SYSTEM' }
    try:
        r = session.get(server + ":" + port + "/semanticturkey/it.uniroma2.art.semanticturkey/st-core-services/Projects/listProjects?", params = payload)
    except (MaxRetryError, ConnectTimeoutError, ConnectTimeout, ReadTimeout):
        logger.error("No server connexion")
        sys.exit()
    if (r.status_code >300) or (r.status_code<200):
        logger.error(r.text)
        sys.exit()
    res = json.loads(r.content)
    if(only_title):
        logger.info("Projects list : ")
        for h,v in res.items():
            for project in v:
                for id, info in project.items():
                    if(id == 'name'):
                        logger.info(info)
    else:
        logger.info(r.text)
    return res

###################################################################
# Close a specific project
###################################################################
def close_project(project_name):
    global logger
    payload = {'consumer': 'SYSTEM', 'projectName': project_name}
    r = session.post(server + ":" + port + "/semanticturkey/it.uniroma2.art.semanticturkey/st-core-services/Projects/disconnectFromProject?",
        params=payload)
    logger.info(r.content)
    return

###################################################################
# open a specific project
###################################################################
def open_project(project_name):
    
    info = connection()
    global logger
    
    if not _check_if_Project(project_name):
        return False
    
    payload = {'consumer': 'SYSTEM', 'projectName': project_name, 'requestedAccessLevel': 'RW',
               'requestedLockLevel': 'NO'}
    r = session.post(server + ":" + port + "/semanticturkey/it.uniroma2.art.semanticturkey/st-core-services/Projects/accessProject?",
        params=payload)
    logger.info(r.content)
    
    payload = {'properties': 'active_schemes,active_lexicon,show_flags,show_instances_number,project_theme,search_languages,search_restrict_lang,search_include_locales,search_use_autocomplete,class_tree_filter_enabled,class_tree_filter_map,class_tree_root,concept_tree_base_broader_prop,concept_tree_broader_props,concept_tree_narrower_props,concept_tree_include_subprops,concept_tree_sync_inverse,concept_tree_visualization,lex_entry_list_visualization,lex_entry_list_index_lenght,editing_language',
               'ctx_project': project_name}
    r = session.get(server + ":" + port + "/semanticturkey/it.uniroma2.art.semanticturkey/st-core-services/PreferencesSettings/getPUSettings?",
        params=payload)
    logger.info(r.content)
    
    payload = {'properties': 'languages', 'pluginID' :'it.uniroma2.art.semanticturkey.plugin.extpts.RenderingEngine', 'ctx_project': project_name}
    r = session.get(server + ":" + port + "/semanticturkey/it.uniroma2.art.semanticturkey/st-core-services/PreferencesSettings/getPUSettings?",
        params=payload)
    logger.info(r.content)
    
    payload = {'properties': 'languages', 'ctx_project': project_name}
    r = session.get(server + ":" + port + "/semanticturkey/it.uniroma2.art.semanticturkey/st-core-services/PreferencesSettings/getProjectSettings?",
        params=payload)
    logger.info(r.content)
    
    payload = {'projectName': project_name, 'email': info["result"]["email"], 'ctx_project':project_name}
    r = session.get(server + ":" + port + "/semanticturkey/it.uniroma2.art.semanticturkey/st-core-services/Administration/getProjectUserBinding?",
        params=payload)
    logger.info(r.content)
    
    payload = {'ctx_project': project_name}
    r = session.get(server + ":" + port + "/semanticturkey/it.uniroma2.art.semanticturkey/st-core-services/Collaboration/getCollaborationSystemStatus?",
        params=payload)
    logger.info(r.content)
    
    r = session.get(server + ":" + port + "/semanticturkey/it.uniroma2.art.semanticturkey/st-core-services/Users/listUserCapabilities?",
        params=payload)
    logger.info(r.content)
    
    r = session.get(server + ":" + port + "/semanticturkey/it.uniroma2.art.semanticturkey/st-core-services/Metadata/getNamespaceMappings?",
        params=payload)
    logger.info(r.content)
    
    return True
    
###################################################################
# Upload data into a specific project.
###################################################################
def data_upload(data_file="", project = "", base_URI = ""):

    connection()
    global session
    global data_folder
    global templates_folder
    global logger
    pathF = ""

    if (os.path.exists(os.path.join(data_folder, data_file))):
            pathF = data_folder + "/" + data_file
    
    opened = False
    if (_check_if_Project(project)):
        opened = open_project(project)
        
    if ((pathF != "") & (project != "") & opened):
        if (_check_if_data(project)):
            logger.error("the project " + project + " contains already some data")

        payload = {'ctx_project': project, 'extensionPointID' :'it.uniroma2.art.semanticturkey.extension.extpts.rdftransformer.RDFTransformer'}
        r = session.get(server + ":" + port + "/semanticturkey/it.uniroma2.art.semanticturkey/st-core-services/Extensions/getExtensions?",
            params=payload)
        
        logger.info(r.content)
        
        payload = {'ctx_project': project, 'extensionPointID':'it.uniroma2.art.semanticturkey.extension.extpts.loader.RepositoryTargetingLoader'}
        r = session.get(server + ":" + port + "/semanticturkey/it.uniroma2.art.semanticturkey/st-core-services/Extensions/getExtensions?",
            params=payload)
        logger.info(r.content)

        payload = {'ctx_project': project, 'extensionPointID': 'it.uniroma2.art.semanticturkey.extension.extpts.loader.StreamTargetingLoader'}
        r = session.get(server + ":" + port + "/semanticturkey/it.uniroma2.art.semanticturkey/st-core-services/Extensions/getExtensions?",
            params=payload)
        logger.info(r.content)

        payload = {'ctx_project': project, 'extensionPointID': 'it.uniroma2.art.semanticturkey.extension.extpts.rdflifter.RDFLifter'}
        r = session.get(server + ":" + port + "/semanticturkey/it.uniroma2.art.semanticturkey/st-core-services/Extensions/getExtensions?",
            params=payload)
        logger.info(r.content)
        
        payload = {'ctx_project': project, 'extensionID': 'it.uniroma2.art.semanticturkey.extension.impl.rdflifter.rdfdeserializer.RDFDeserializingLifter'}
        r = session.get(server + ":" + port + "/semanticturkey/it.uniroma2.art.semanticturkey/st-core-services/InputOutput/getSupportedFormats?",
            params=payload)
        logger.info(r.content)
        
        payload = {'ctx_project': project}
        format = _formatExtraction(pathF, project)
        
        if (base_URI == ""):
            base_URI = get_base_URI_from_project(project)
        if (base_URI == "") or  (base_URI == None):
            logger.error("The base URI of the project is not defined - The data cannot be uploaded")
            sys.exit()
        data = {'baseURI': base_URI, 'transitiveImportAllowance': 'web',
                'format': format, 'rdfLifterSpec':'{"factoryId":"it.uniroma2.art.semanticturkey.extension.impl.rdflifter.rdfdeserializer.RDFDeserializingLifter"}',
                'transformationPipeline': '[]', 'validateImplicitly':'true'}
        fields = {'inputFile': (pathF, open(pathF, 'rb'))}
        r = session.post(server + ":" + port + "/semanticturkey/it.uniroma2.art.semanticturkey/st-core-services/InputOutput/loadRDF?",
            files=fields, data=data, params=payload)
        
        logger.info(r.content)
        
        logger.info("Upload in the project " + project + " is well achieved")

        payload = {'ctx_project': project, 'classList': '<http://www.w3.org/2002/07/owl#Thing>'}
        r = session.get(server + ":" + port + "/semanticturkey/it.uniroma2.art.semanticturkey/st-core-services/Classes/getClassesInfo?",
            params=payload)
        logger.info(r.content)

        payload = {'ctx_project': project}
        r = session.get(server + ":" + port + "/semanticturkey/it.uniroma2.art.semanticturkey/st-core-services/Properties/getTopProperties?",
            params=payload)
        logger.info(r.content)
        r = session.get(server + ":" + port + "/semanticturkey/it.uniroma2.art.semanticturkey/st-core-services/Datatypes/getDeclaredDatatypes?",
            params=payload)
        logger.info(r.content)

        payload = {'ctx_project': project, 'schemes':'', 'broaderProps':'', 'narrowerProps':'', 'includeSubProperties':'true'}
        r = session.get(server + ":" + port + "/semanticturkey/it.uniroma2.art.semanticturkey/st-core-services/SKOS/getTopConcepts?",
            params=payload)
        logger.info(r.content)
        
        payload = {'ctx_project': project}
        r = session.get(server + ":" + port + "/semanticturkey/it.uniroma2.art.semanticturkey/st-core-services/SKOS/getAllSchemes?",
            params=payload)
        logger.info(r.content)
        r = session.get(server + ":" + port + "/semanticturkey/it.uniroma2.art.semanticturkey/st-core-services/SKOS/getRootCollections?",
            params=payload)
        logger.info(r.content)

        #validate_all(project)
        
    return

############################
# Ask a question to the user
############################
def ask_question(message):
    answer = None
    while answer not in ("y", "Y", "N", "n"):
        answer = input(message)
        if answer in ("y", "Y"):
            return True
        elif answer in ("n", "N"):
            return False
    return

#############################################################################
# Get the namespaces from the mentionned project
############################################################################
def get_namespace(project):

    connection()
    global session
    global logger
    global server
    global port

    payload = {'ctx_project': project}
    if (_check_if_Project(project)):
        r = session.get(server + ":" + port + "/semanticturkey/it.uniroma2.art.semanticturkey/st-core-services/Metadata/getNamespaceMappings?", params=payload)
        res = json.loads(r.content)
        for k, v in res.items():
            for namespace in v:
                logger.info(namespace)
            return v
    return None

#############################################################################
# Add the specified name space to the designed project
############################################################################
def add_namespace(project_name, prefix, namespace):
    connection()
    global session
    global fileFolder
    global data_folder
    global logger
    open_project(project_name)

    payload = {'ctx_project': project_name}
    r = session.get(server + ":" + port + "/semanticturkey/it.uniroma2.art.semanticturkey/st-core-services/Metadata/getBaseURI?",
        params=payload)

    logger.info(r.content)

    r = session.get(server + ":" + port + "/semanticturkey/it.uniroma2.art.semanticturkey/st-core-services/Metadata/getDefaultNamespace?",
        params=payload)

    logger.info(r.content)
    
    r = session.get(server + ":" + port + "/semanticturkey/it.uniroma2.art.semanticturkey/st-core-services/Metadata/getImports?",
        params=payload)

    logger.info(r.content)
    
    r = session.get(server + ":" + port + "/semanticturkey/it.uniroma2.art.semanticturkey/st-core-services/Metadata/getNamespaceMappings?",
        params=payload)

    logger.info(r.content)
    
    base_URI = get_base_URI_from_project(project_name)
    
    payload = {'ctx_project': project_name, 'includeInferred': 'false', 'resource' : "<" + base_URI + ">"}
    r = session.get(server + ":" + port + "/semanticturkey/it.uniroma2.art.semanticturkey/st-core-services/ResourceView/getResourceView?",
        params=payload)

    logger.info(r.content)
    
    payload = {'ctx_project': project_name}
    r = session.get(server + ":" + port + "/semanticturkey/it.uniroma2.art.semanticturkey/st-core-services/Metadata/getImports?",
        params=payload)
    
    logger.info(r.content)
    
    r = session.get(server + ":" + port + "/semanticturkey/it.uniroma2.art.semanticturkey/st-core-services/Metadata/getNamespaceMappings?",
        params=payload)
    
    logger.info(r.content)
    
    payload = {'ctx_project': project_name, 'prefix':prefix, 'namespace':namespace}
    r = session.post(server + ":" + port + "/semanticturkey/it.uniroma2.art.semanticturkey/st-core-services/Metadata/setNSPrefixMapping?", params=payload)
    close_project(project_name)
    
    logger.info(r.content)
    
    r = session.get(server + ":" + port + "/semanticturkey/it.uniroma2.art.semanticturkey/st-core-services/Metadata/getNamespaceMappings?",
        params=payload)
    
    logger.info(r.content)
    
    logger.info("The namespace : " + str(namespace) + " was added to the project " + project_name + " with the prefix : " + prefix)
    return

########################################################################
# Detect the type of the file
########################################################################
def file_type(file_name):
    elt_list = file_name.split(".")
    return elt_list[len(elt_list) - 1].strip()

########################################################################
# Return the list of the namespaces into a RDF file
########################################################################
def parse_nspace_rdf(file_name):
    global data_folder
    pathF = ""
    if os.path.exists(file_name):
        pathF = file_name
    elif (os.path.exists(data_folder + "/" + file_name)):
        pathF = data_folder + "/" + file_name
    final = ""
    with open(pathF, encoding='utf8') as f:
        lines = f.readlines()
    i = 0
 
    if len(lines) > 500:
        size = 500
    else:
        size = len(lines) - 2
    while (i < size):
        final = final + "\n" + lines[i]
        i += 1
        
    n_spaces = {}
    extraction = re.findall("<rdf:RDF.*>", final, re.DOTALL)
    
    declaration = re.findall("xmlns.*\s", extraction[0])
    
    for d in declaration:
        prefix = d.split("=",1)[0]
        prefix = re.sub("xmlns", "", prefix)
        prefix = re.sub(":", "", prefix)
        name_space = d.split("=",1)[1]
        name_space = name_space.strip()
        name_space = name_space.strip("\"")
        name_space = name_space.strip("<")
        name_space = name_space.strip(">")
        if len(str(prefix).strip()) == 0:
            n_spaces["  "] = name_space
        else:
            n_spaces[prefix] = name_space
    return n_spaces

########################################################################
# Return the list of the namespaces into a ttl file
########################################################################
def parse_nspace_ttl(file_name):
    global data_folder
    pathF = data_folder + "/" + file_name
    n_spaces = {}
    final = ""
    with open(pathF, encoding='utf8') as f:
        lines = f.readlines()
    
    for line in lines:
        l = line.strip()
        if (len(l) == 0):
            continue
        if l[0] == '#':
            continue
        final = final + "\n" + line
    
    declaration = re.findall("@prefix.*>[\s\n]*?\.", final)
    
    for d in declaration:
        prefix = d.split(":",1)[0]
        prefix = re.sub("@prefix", "", prefix)
        name_space = d.split(":",1)[1]
        name_space = name_space.strip(".")
        name_space = name_space.strip()
        name_space = name_space.strip("<")
        name_space = name_space.strip(">")
        if len(str(prefix).strip()) == 0:
            n_spaces["  "] = name_space
        else:
            n_spaces[prefix] = name_space
    for n, v in n_spaces.items():
        print(n + ":" + v)
    return n_spaces

###############################################
# Create and import a custom form
##############################################
def createForm(project, form):
    connection()
    global session
    global logger
    global custom_forms
    
    open_project(project)
    
    payload = {'ctx_project': project}
    r = session.get(server + ":" + port + "/semanticturkey/it.uniroma2.art.semanticturkey/st-core-services/CustomForms/getCustomFormConfigMap?",
        params=payload)

    logger.info(r.content)
    
    r = session.get(server + ":" + port + "/semanticturkey/it.uniroma2.art.semanticturkey/st-core-services/CustomForms/getAllFormCollections?",
        params=payload)

    logger.info(r.content)
    
    r = session.get(server + ":" + port + "/semanticturkey/it.uniroma2.art.semanticturkey/st-core-services/CustomForms/getAllCustomForms?",
        params=payload)

    logger.info(r.content)
    
    payload = {'ctx_project': project, 'formType':'graph', 'pearl' : custom_forms[form]}

    r = session.post(server + ":" + port + "/semanticturkey/it.uniroma2.art.semanticturkey/st-core-services/CustomForms/validatePearl?",
        params=payload)

    logger.info(r.content)
    
    payload = {'ctx_project': project, 'type' : 'graph', 'id':'it.uniroma2.art.semanticturkey.customform.form.reifiednotes1', 'name': 'reifiednotes1',
               'description': 'reifiednotes1', 'ref' : custom_forms[form], 'showPropChain' : '<http://www.w3.org/1999/02/22-rdf-syntax-ns#value>'}
    r = session.post(server + ":" + port + "/semanticturkey/it.uniroma2.art.semanticturkey/st-core-services/CustomForms/createCustomForm?",
        params=payload)

    logger.info(r.content)
    
    payload = {'ctx_project': project}
    r = session.get(server + ":" + port + "/semanticturkey/it.uniroma2.art.semanticturkey/st-core-services/CustomForms/getAllCustomForms?",
        params=payload)

    logger.info(r.content)
    
    r = session.get(server + ":" + port + "/semanticturkey/it.uniroma2.art.semanticturkey/st-core-services/CustomForms/getAllCustomForms?",
        params=payload)

    logger.info(r.content)
    
    payload = {'ctx_project': project, 'id':'it.uniroma2.art.semanticturkey.customform.collection.reifiednotes1'}
    r = session.get(server + ":" + port + "/semanticturkey/it.uniroma2.art.semanticturkey/st-core-services/CustomForms/createFormCollection?",
        params=payload)

    logger.info(r.content)
    
    payload = {'ctx_project': project, 'formCollectionId' : 'it.uniroma2.art.semanticturkey.customform.collection.reifiednotes1',
               'customFormIds' : 'it.uniroma2.art.semanticturkey.customform.form.reifiednotes1',
               'suggestions' : ''}
    r = session.post(server + ":" + port + "/semanticturkey/it.uniroma2.art.semanticturkey/st-core-services/CustomForms/updateFromCollection?",
            params=payload)

    logger.info(r.content)
    
    payload = {'ctx_project': project}
    r = session.get(server + ":" + port + "/semanticturkey/it.uniroma2.art.semanticturkey/st-core-services/CustomForms/getAllFormCollections?",
        params=payload)
    logger.info(r.content)
    
    r = session.get(server + ":" + port + "/semanticturkey/it.uniroma2.art.semanticturkey/st-core-services/CustomForms/getAllFormCollections?",
        params=payload)
    logger.info(r.content)
    
    r = session.get(server + ":" + port + "/semanticturkey/it.uniroma2.art.semanticturkey/st-core-services/Properties/getTopProperties?",
        params=payload)
    logger.info(r.content)
    
    payload = {'ctx_project': project, 'superProperty' : '<http://www.w3.org/2004/02/skos/core#note>'}
    r = session.get(server + ":" + port + "/semanticturkey/it.uniroma2.art.semanticturkey/st-core-services/Properties/getSubProperties?",
        params=payload)
    logger.info(r.content)
    
    payload = {'ctx_project': project, 'formCollId':'it.uniroma2.art.semanticturkey.customform.collection.reifiednotes1', 'resource' : '<http://www.w3.org/2004/02/skos/core#definition>'}
    r = session.get(server + ":" + port + "/semanticturkey/it.uniroma2.art.semanticturkey/st-core-services/CustomForms/addFormsMapping?",
        params=payload)
    logger.info(r.content)
    
    payload = {'ctx_project': project}
    r = session.get(server + ":" + port + "/semanticturkey/it.uniroma2.art.semanticturkey/st-core-services/CustomForms/getCustomFormConfigMap?",
        params=payload)
    logger.info(r.content)
    
    r = session.get(server + ":" + port + "/semanticturkey/it.uniroma2.art.semanticturkey/st-core-services/CustomForms/getAllFormCollections?",
        params=payload)
    logger.info(r.content)
    
    r = session.get(server + ":" + port + "/semanticturkey/it.uniroma2.art.semanticturkey/st-core-services/Properties/getTopProperties?",
        params=payload)
    logger.info(r.content)

    payload = {'ctx_project': project, 'superProperty' : '<http://www.w3.org/2004/02/skos/core#note>'}
    r = session.get(server + ":" + port + "/semanticturkey/it.uniroma2.art.semanticturkey/st-core-services/Properties/getSubProperties?",
        params=payload)
    logger.info(r.content)
    
    payload = {'ctx_project': project, 'formCollId' : 'it.uniroma2.art.semanticturkey.customform.collection.reifiednotes1' , 'resource':'<http://www.w3.org/2004/02/skos/core#changeNote>'}
    r = session.get(server + ":" + port + "/semanticturkey/it.uniroma2.art.semanticturkey/st-core-services/CustomForms/addFormsMapping?",
        params=payload)
    logger.info(r.content)
    
    payload = {'ctx_project': project}
    r = session.get(server + ":" + port + "/semanticturkey/it.uniroma2.art.semanticturkey/st-core-services/CustomForms/getCustomFormConfigMap?",
        params=payload)
    logger.info(r.content)
    
    r = session.get(server + ":" + port + "/semanticturkey/it.uniroma2.art.semanticturkey/st-core-services/CustomForms/getAllFormCollections?",
        params=payload)
    logger.info(r.content)
    
    r = session.get(server + ":" + port + "/semanticturkey/it.uniroma2.art.semanticturkey/st-core-services/Properties/getTopProperties?",
        params=payload)
    logger.info(r.content)

    payload = {'ctx_project': project, 'superProperty' : '<http://www.w3.org/2004/02/skos/core#note>'}
    r = session.get(server + ":" + port + "/semanticturkey/it.uniroma2.art.semanticturkey/st-core-services/Properties/getSubProperties?",
        params=payload)
    logger.info(r.content)
    
    payload = {'ctx_project': project, 'formCollId' : 'it.uniroma2.art.semanticturkey.customform.collection.reifiednotes1', 'resource' :'<http://www.w3.org/2004/02/skos/core#editorialNote>'}
    r = session.get(server + ":" + port + "/semanticturkey/it.uniroma2.art.semanticturkey/st-core-services/CustomForms/addFormsMapping?",
        params=payload)
    logger.info(r.content)

    payload = {'ctx_project': project}
    r = session.get(server + ":" + port + "/semanticturkey/it.uniroma2.art.semanticturkey/st-core-services/CustomForms/getCustomFormConfigMap?",
        params=payload)
    logger.info(r.content)
    
    r = session.get(server + ":" + port + "/semanticturkey/it.uniroma2.art.semanticturkey/st-core-services/CustomForms/getAllFormCollections?",
        params=payload)
    logger.info(r.content)
    
    r = session.get(server + ":" + port + "/semanticturkey/it.uniroma2.art.semanticturkey/st-core-services/Properties/getTopProperties?",
        params=payload)
    logger.info(r.content)

    payload = {'ctx_project': project, 'superProperty' : '<http://www.w3.org/2004/02/skos/core#note>'}
    r = session.get(server + ":" + port + "/semanticturkey/it.uniroma2.art.semanticturkey/st-core-services/Properties/getSubProperties?",
        params=payload)
    logger.info(r.content)
    
    payload = {'ctx_project': project, 'formCollId' : 'it.uniroma2.art.semanticturkey.customform.collection.reifiednotes1', 'resource':'<http://www.w3.org/2004/02/skos/core#example>'}
    r = session.get(server + ":" + port + "/semanticturkey/it.uniroma2.art.semanticturkey/st-core-services/CustomForms/addFormsMapping?",
        params=payload)
    logger.info(r.content)
    
    payload = {'ctx_project': project}
    r = session.get(server + ":" + port + "/semanticturkey/it.uniroma2.art.semanticturkey/st-core-services/CustomForms/getCustomFormConfigMap?",
        params=payload)
    logger.info(r.content)
    
    r = session.get(server + ":" + port + "/semanticturkey/it.uniroma2.art.semanticturkey/st-core-services/CustomForms/getAllFormCollections?",
        params=payload)
    logger.info(r.content)
    
    r = session.get(server + ":" + port + "/semanticturkey/it.uniroma2.art.semanticturkey/st-core-services/Properties/getTopProperties?",
        params=payload)
    logger.info(r.content)

    payload = {'ctx_project': project, 'superProperty':'<http://www.w3.org/2004/02/skos/core#note>'}
    r = session.get(server + ":" + port + "/semanticturkey/it.uniroma2.art.semanticturkey/st-core-services/Properties/getSubProperties?",
        params=payload)
    logger.info(r.content)
    
    payload = {'ctx_project': project, 'formCollId':'it.uniroma2.art.semanticturkey.customform.collection.reifiednotes1', 'resource':'<http://www.w3.org/2004/02/skos/core#historyNote>', }
    r = session.get(server + ":" + port + "/semanticturkey/it.uniroma2.art.semanticturkey/st-core-services/CustomForms/addFormsMapping?",
        params=payload)
    logger.info(r.content)

    payload = {'ctx_project': project}
    r = session.get(server + ":" + port + "/semanticturkey/it.uniroma2.art.semanticturkey/st-core-services/CustomForms/getCustomFormConfigMap?",
        params=payload)
    logger.info(r.content)
    
    r = session.get(server + ":" + port + "/semanticturkey/it.uniroma2.art.semanticturkey/st-core-services/CustomForms/getAllFormCollections?",
        params=payload)
    logger.info(r.content)
    
    r = session.get(server + ":" + port + "/semanticturkey/it.uniroma2.art.semanticturkey/st-core-services/Properties/getTopProperties?",
        params=payload)
    logger.info(r.content)
    
    payload = {'ctx_project': project,'superProperty': '<http://www.w3.org/2004/02/skos/core#note>'}
    r = session.get(server + ":" + port + "/semanticturkey/it.uniroma2.art.semanticturkey/st-core-services/Properties/getSubProperties?",
        params=payload)
    logger.info(r.content)
    
    payload = {'ctx_project': project, 'formCollId': 'it.uniroma2.art.semanticturkey.customform.collection.reifiednotes1', 'resource': '<http://www.w3.org/2004/02/skos/core#scopeNote>'}
    r = session.get(server + ":" + port + "/semanticturkey/it.uniroma2.art.semanticturkey/st-core-services/CustomForms/addFormsMapping?",
        params=payload)
    logger.info(r.content)

    payload = {'ctx_project': project}
    r = session.get(server + ":" + port + "/semanticturkey/it.uniroma2.art.semanticturkey/st-core-services/CustomForms/getCustomFormConfigMap?",
        params=payload)
    logger.info(r.content)
    r = session.get(server + ":" + port + "/semanticturkey/it.uniroma2.art.semanticturkey/st-core-services/CustomForms/getAllFormCollections?",
        params=payload)
    logger.info(r.content)
    r = session.get(server + ":" + port + "/semanticturkey/it.uniroma2.art.semanticturkey/st-core-services/Properties/getTopProperties?",
        params=payload)
    logger.info(r.content)
    
    payload = {'ctx_project': project,'formCollId': 'it.uniroma2.art.semanticturkey.customform.collection.reifiednotes1','resource': '<http://www.w3.org/2004/02/skos/core#note>'}
    r = session.get(server + ":" + port + "/semanticturkey/it.uniroma2.art.semanticturkey/st-core-services/CustomForms/addFormsMapping?",
        params=payload)
    logger.info(r.content)

    payload = {'ctx_project': project}
    r = session.get(server + ":" + port + "/semanticturkey/it.uniroma2.art.semanticturkey/st-core-services/CustomForms/getCustomFormConfigMap?",
        params=payload)
    logger.info(r.content)

    payload = {'ctx_project': project, 'resource' : '<http://www.w3.org/2004/02/skos/core#changeNote>', 'replace' : 'true'}
    r = session.get(server + ":" + port + "/semanticturkey/it.uniroma2.art.semanticturkey/st-core-services/CustomForms/updateReplace?",
        params=payload)
    logger.info(r.content)

    payload = {'ctx_project': project,'resource': '<http://www.w3.org/2004/02/skos/core#definition>', 'replace': 'true'}
    r = session.get(server + ":" + port + "/semanticturkey/it.uniroma2.art.semanticturkey/st-core-services/CustomForms/updateReplace?",
        params=payload)
    logger.info(r.content)

    payload = {'ctx_project': project,'resource': '<http://www.w3.org/2004/02/skos/core#editorialNote>', 'replace': 'true'}
    r = session.get(server + ":" + port + "/semanticturkey/it.uniroma2.art.semanticturkey/st-core-services/CustomForms/updateReplace?",
        params=payload)
    logger.info(r.content)

    payload = {'ctx_project': project,'resource': '<http://www.w3.org/2004/02/skos/core#example>', 'replace': 'true'}
    r = session.get(server + ":" + port + "/semanticturkey/it.uniroma2.art.semanticturkey/st-core-services/CustomForms/updateReplace?",
        params=payload)
    logger.info(r.content)

    payload = {'ctx_project': project, 'resource': '<http://www.w3.org/2004/02/skos/core#historyNote>','replace': 'true'}
    r = session.get(server + ":" + port + "/semanticturkey/it.uniroma2.art.semanticturkey/st-core-services/CustomForms/updateReplace?",
        params=payload)
    logger.info(r.content)

    payload = {'ctx_project': project,'resource': '<http://www.w3.org/2004/02/skos/core#note>', 'replace': 'true'}
    r = session.get(server + ":" + port + "/semanticturkey/it.uniroma2.art.semanticturkey/st-core-services/CustomForms/updateReplace?",
        params=payload)
    logger.info(r.content)

    payload = {'ctx_project': project, 'resource': '<http://www.w3.org/2004/02/skos/core#scopeNote>','replace': 'true'}
    r = session.get(server + ":" + port + "/semanticturkey/it.uniroma2.art.semanticturkey/st-core-services/CustomForms/updateReplace?",
        params=payload)
    logger.info(r.content)
    
    return

#####################################################################
# Validate all the action done (project creation, ontology import...)
#####################################################################
def validate_all(project_name):
    connection()
    global session
    global logger
    
    open_project(project_name)
    
    payload = {'ctx_project': project_name, 'limit':'100', 'operationFilter':''}
    r = session.get(server + ":" + port + "/semanticturkey/it.uniroma2.art.semanticturkey/st-core-services/Validation/getStagedCommitSummary?",
        params=payload)

    logger.info(r.content)
    
    payload = {'timeUpperBound':'2050-04-01T08:36:00.674Z', 'operationSorting':'Unordered',
               'timeSorting': 'Descending', 'page' :'0', 'ctx_project': project_name, 'limit': '100', 'operationFilter': ''}
    r = session.get(server + ":" + port + "/semanticturkey/it.uniroma2.art.semanticturkey/st-core-services/Validation/getCommits?",
        params=payload)

    logger.info(r.content)

    results = json.loads(r.text)
    commits = results["result"]
    for c in commits:
        if c['commit'] == None:
            logger.error("Erreur de validation de l'ontologie")
            continue
        
        payload = {'validatableCommit': "<"+c['commit'] + ">", 'ctx_project': project_name}
        r = session.post(server + ":" + port + "/semanticturkey/it.uniroma2.art.semanticturkey/st-core-services/Validation/accept?",
            params=payload)

        logger.info(r.content)

    payload = {'ctx_project': project_name, 'limit': '100', 'operationFilter': ''}
    r = session.get(server + ":" + port + "/semanticturkey/it.uniroma2.art.semanticturkey/st-core-services/Validation/getStagedCommitSummary?",
        params=payload)

    logger.info(r.content)
    
    return
    
###############################################
# import a specific Ontology into the system
##############################################
def importOntology(project_name = ""):
    connection()
    global session
    global logger
    global files_folder
    global ontologies_folder
    
    if (os.path.exists(os.path.join(files_folder, "Template_Insertion_Ontology.csv"))):
        pathF =os.path.join(files_folder, "Template_Insertion_Ontology.csv")
    else:
        logger.error("the configuration file for the ontologies cannot be loaded")
        sys.exit()
        
    with codecs.open(pathF, encoding='utf8') as f:
        reader = csv.reader(f, delimiter=';')
        first = True
        for row in reader:
            if first:
                first = False
                continue
            project = row[0]
            
            if (project_name != "") & (project_name != project):
                continue
            #Get the ontology file
            if (os.path.exists(os.path.join(ontologies_folder, row[1]))):
                localFile = os.path.join(ontologies_folder, row[1])
            else:
                logger.error("The ontology " + row[1] + " cannot be found")
                continue
            mirrorFile = str(row[1]).split("1")[0]
            baseURI = row[2]
            #Base URI from the ontology
            if (baseURI == None):
                logger.error("The base URI of the project : " + project + " is not detected")
                continue
            if (_check_if_Project(project)):
                open_project(project)
                
                logger.info("An ontology is added to the project : " + project)
                logger.info("The ontology : " + row[1] + " is currently treated")
                
                payload = {'ctx_project': project, 'baseURI': baseURI, 'mirrorFile': mirrorFile,
                       'transitiveImportAllowance': 'web', 'localFile':localFile}
                fields={'localFile':(row[1], open(localFile , 'rb'), 'multipart/form-data')}
                r = session.post(server + ":" + port + "/semanticturkey/it.uniroma2.art.semanticturkey/st-core-services/Metadata/addFromLocalFile?", files=fields, params=payload)
                
                logger.info(r.content)
                
                payload = {'ctx_project': project}
                r = session.get(server + ":" + port + "/semanticturkey/it.uniroma2.art.semanticturkey/st-core-services/Metadata/getImports?",
                    params=payload)

                logger.info(r.content)
                
                r = session.get(server + ":" + port + "/semanticturkey/it.uniroma2.art.semanticturkey/st-core-services/Metadata/getNamespaceMappings?",
                    params=payload)

                logger.info(r.content)
                
                base_uri_from_project = get_base_URI_from_project(project)
                payload = {'ctx_project': project, 'includeInferred':'true', 'resource': "<" + base_uri_from_project + ">"}
                r = session.get(server + ":" + port + "/semanticturkey/it.uniroma2.art.semanticturkey/st-core-services/ResourceView/getResourceView?",
                    params=payload)

                logger.info(r.content)
                
                payload = {'ctx_project': project}
                r = session.get(server + ":" + port + "/semanticturkey/it.uniroma2.art.semanticturkey/st-core-services/Metadata/getImports?",
                    params=payload)

                logger.info(r.content)
                
                r = session.get(server + ":" + port + "/semanticturkey/it.uniroma2.art.semanticturkey/st-core-services/Metadata/getNamespaceMappings?",
                    params=payload)

                logger.info(r.content)
                
                validate_all(project)
                
                close_project(project)
            else:
                print("The project is not available")
    return

################################################
# Return the base URI based on the project Name
################################################
def get_base_URI_from_project(project_name):
    
    res = list_of_project(only_title = False)
    result = res['result']
    for r in result:
        if (r['name'] == project_name):
            return r['baseURI']
    return None
################################################
# Check if there is already data in the project
################################################
def _check_if_data(project):

    connection()
    global logger
    global session
    payload = {'ctx_project' : project, 'projectName':project, 'includeSubProperties':'true'}
    r = session.get(server + ":" + port + "/semanticturkey/it.uniroma2.art.semanticturkey/st-core-services/SKOS/getTopConcepts?", params=payload)
    if (r.status_code >300) or (r.status_code<200):
        logger.error(r.text)
        sys.exit()
    else:
        logger.info("project present")
        return True

#####################################################################################
# Check if a project already exist Return True is the project already exist else
#####################################################################################
def _check_if_Project(project):
    connection()
    global session
    global logger
    payload = {'consumer' : 'SYSTEM', 'projectName':project, 'requestedAccessLevel':'R',
               'requestedLockLevel':'NO'}
    r = session.post(server + ":" + port + "/semanticturkey/it.uniroma2.art.semanticturkey/st-core-services/Projects/accessProject?", params=payload)
    if ('it.uniroma2.art.semanticturkey.exceptions.ProjectInexistentException' in r.text):
        logger.error("The project " + project + " is not present")
        return False
    else:
        logger.info("The project " + project + " is present")
        return True

################################################################
# Automatic extraction of the data file format (using Workbench)
################################################################
def _formatExtraction(fileName, project):
    connection()
    global session
    payload = {'fileName': fileName, 'ctx_project': project}
    r = session.get(server + ":" + port + "/semanticturkey/it.uniroma2.art.semanticturkey/st-core-services/InputOutput/getParserFormatForFileName?", params=payload)
    return (json.loads(r.text)['result'])

###################################################################
# Delete the data within the project. Should not be directly called
###################################################################
def clearData(project):
    
    connection()
    global session
    global logger
    payload = {'ctx_project': project}
    r = session.post(server + ":" + port + "/semanticturkey/it.uniroma2.art.semanticturkey/st-core-services/InputOutput/clearData?",
               params = payload)
    
    validate_all(project)
    
    logger.info(r.text)
    return

#############################################
# get the configuration information
#############################################
def get_conf_information():
    with open("./setup.cfg", "r", encoding='utf8') as f:
        lines = f.readlines()
    for line in lines:
        print(line.strip())
    return

#################################################################
# Set the new folder for data (the variable dataFolder is global)
#################################################################
def setDataFolder(folder = ""):

    finalStr = ""
    oldFolder = ""
    global logger
    global dataFolder
    global log_folder

    dataFolder = folder
    
    if (dataFolder == ""):
        print("The new folder is not defined")
        sys.exit()

    #Change the configuration into the setup.cfg file
    with open("./setup.cfg", "r", encoding='utf8') as f:
        lines = f.readlines()
    for line in lines:
        if "DATA_DIR=" in line:
            oldFolder = re.sub("DATA_DIR", "", line).strip()
    if (oldFolder == ""):
        print("The configuration file is not well-formed")
        sys.exit()
    
    #Check the input
    dataFolder = dataFolder.replace("\\","/")
    dataFolder = dataFolder.rstrip("/")
    dataFolder = dataFolder + "/"
    
    # modify the config file
    for line in lines:
        if ("_DIR" in line):
            tmp = re.sub(oldFolder, "=" + dataFolder ,line)
            finalStr += tmp
        else:
            finalStr += line
    with open("./setup.cfg", "w", encoding='utf8') as f:
        f.write(finalStr)
    
    #Create the new folders automatically
    # Main data folder
    if (not os.path.exists(dataFolder)):
        os.mkdir(dataFolder)
    # Log folder
    if (not os.path.exists(os.path.join(dataFolder, "log"))):
        os.mkdir(dataFolder+"log")
    else:
        logger.info("The log folder already exists")
    current_log_folder = log_folder.rstrip("/")
    current_log_folder = current_log_folder + "/"
    shutil.copy(current_log_folder + "logFile.txt", dataFolder + "log/logFile.txt")
    
    # Files folder
    if (not os.path.exists(os.path.join(dataFolder, "files"))):
        os.mkdir(dataFolder + "files")
    else:
        logger.info("The files folder already exists")

    #Ontologies folder
    
    #Customs_form folders
    
    
    set_configuration()
    
    return

##################################################################
# Configure the logger inside the systems
##################################################################
def set_logger():


    global log_folder
    global logger
    global ch

    logger = logging.getLogger('VBController')
    logger.setLevel(logging.INFO)
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    logger.addHandler(ch)

    if (os.path.exists(os.path.join(log_folder, "logfile.txt"))):
        pathF =os.path.join(log_folder, "logfile.txt")
        fh = logging.FileHandler(pathF)
    else:
        logger.error("Unable to find the log files - wrong configuration")
        sys.exit()
    logger.addHandler(fh)
    logger.info("The logger for the console is set")
    return

#############################################
# Main function
#############################################
def main(argv):

    global dataFile
    global dataFolder

    set_configuration()
    set_logger()

    try:
        opts, args = getopt.getopt(sys.argv[1:],"a:cde:f:ghik:lm:no:pq:u:vs:txv:",["setDataFd=","name_list=", "projectsFile=", "data=", "-clearData="])
    except getopt.GetoptError:
        print ('AutoProject.py -d <datafile>')
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            usagePrint()
            sys.exit()
        # Validate all
        elif opt in ("-a"):
            project_name = arg
            validate_all(project_name)
        #Connect to the server
        elif opt in ("-c"):
            connection()
        # Create a new project
        elif opt in ("-d", "--projectFiles"):
            project_creation()
        #Modify the datafolder
        elif opt in ("-f", "--setDataFd"):
            new_folder = arg
            setDataFolder(new_folder)
        #Print the list of the available projects into Vocbench
        elif opt in ("-l", "--list"):
            list_of_project(only_title = False)
        #Print the title of the available projects into Vocbench
        elif opt in ("-n", "--name_list"):
            list_of_project(only_title = True)
        elif opt in ("-u", "--upLoad"):
            data_file = arg
            project = args[0]
            baseURI = args[1]
            data_upload(data_file, project, baseURI)
        elif opt in ("-g"):
            get_conf_information()
        elif opt in ("-s"):
            project_name = arg
            prefix = args[0]
            namespace = args[1]
            add_namespace(project_name, prefix, namespace)
        elif opt in ("-q"):
            projectName = arg
            get_namespace(projectName)
        elif opt in ("-m"):
            clearData(arg)
        elif opt in ("-o"):
            project_name = arg
            importOntology(project_name)
        elif opt in ("-t"):
            parse_nspace_ttl("euvoc.ttl")
        elif opt in ("-v"):
            parse_nspace_rdf("languages-source-ap.rdf")
        elif opt in ("-e"):
            project = arg
            form = args[0]
            createForm(project, form)
        elif opt in ("-k"):
            project = arg
            open_project(project)
        elif opt in ("-x"):
            project = arg
            validate_all(project)
        else:
            assert False, "unhandled option"

    return

def usagePrint():
    print('Usage :')
    print('     $ python AutoProject.py  [option] \n')
    print('Commands :')
    print('     -h                                  Help.')
    print('     -a project_name                     Validate all the pending actions (corresponding to a specific project).')
    print('     -c                                  Connexion test on the server.')
    print('     -l, --list                          List of all the project inside VocBench.')
    print('     -n, --name_list                     List of all the projects inside VocBench (names only).')
    print('     -p                                  Create projects inside VocBench.')
    print('     -f, --setDataFd  <newPath>          Set the path of the folder where the data have to be set.')
    print('     -d <datafile>                       Create new projects based on the information placed into ')
    print('                                         the file Template_Creation_Projects.csv or inside <datafile>')
    print('     -u                                  upload data using the configuration file Template_Insertion_Data.csv')
    print('     -m                                  delete data from a specific project')
    print('     -o                                  import ontologies describe in the file Template_Insertion__Ontology.csv')
    print('     -x                                  validate all the pending actions')
    print('     -s  project_name prefix namespace   add namespaces')

if __name__ == "__main__":

    main(sys.argv[1:])
    print("The end")