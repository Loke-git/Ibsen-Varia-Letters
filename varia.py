#!/usr/bin/env python
# coding: utf-8
import sys
import subprocess
import pkg_resources

# Package installation borrowed from:
# https://stackoverflow.com/questions/12332975/installing-python-module-within-code/58040520#58040520
required  = {'bs4', 'pandas'} 
installed = {pkg.key for pkg in pkg_resources.working_set}
missing   = required - installed
if missing:
    # implement pip as a subprocess:
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', *missing])

import pandas as pd
from bs4 import BeautifulSoup as bs
import re
from collections import defaultdict

with open("varia.xml", "r", encoding="utf-8") as file:
    # Read each line in the file, readlines() returns a list of lines
    content = file.readlines()
    # Combine the lines in the list into a string
    content = "".join(content)
    soup = bs(content, "xml")
with open("navneregister.xml", "r", encoding="utf-8") as file:
    # Read each line in the file, readlines() returns a list of lines
    content = file.readlines()
    # Combine the lines in the list into a string
    content = "".join(content)
    registry = bs(content, "xml")
d = defaultdict(dict)

docDates,regDates,mscontentscount,biblcount = 0,0,0,0
i=0
print("Working...")
for item in soup.findAll("TEI"): # For every TEI element (every document) in the xml file:
    itemDate = "N/A" # I don't think this is required
    itemType = item['subtype'] # Check the subtype of the document
    if itemType == "dedication" or itemType == "greeting": # Include dedications and greetings only
        xmlid = item['xml:id'] # Find the XML ID of the document
        #print(item["xml:id"])
        
        # First off, try to find the title in the bibl element.
        try: # Try clause because title = None will throw an exception
            bibl = item.find("bibl")
            title = bibl.find("title")
            #print("Title in bibl element")
            biblcount += 1
        # If exception, there's no title in bibl. Look for title in msContents:
        except:
            bibl = item.find("msContents")
            title = bibl.find("title")
            #print("Title in msContents element")
            mscontentscount += 1
        # With the title, unwrap any subelements
        for match in title.findAll():
            match.unwrap()
        newTitle = ""
        for x in title.contents: # Split and recombine the title into 1 whole string
            newTitle+=" "+x
        newTitle = re.sub(' +', ' ',newTitle) # Remove double+ spaces
        title = newTitle.strip() # Remove spaces around the title
        title = re.sub('\n',"",title) # Remove \n
        itemDate = item.find("docDate") # Look for the date in docDate element
        try: # If no docDate, will throw exception
            xmldate = itemDate['when']
            docDates+=1

        except: # No docDate? Look for date in date element
            itemDate = item.find("date")
            xmldate = itemDate['when']
            regDates+=1
        date = itemDate['when']
        datenumbers = xmldate.replace("-","") # Get the numbers only from the date (1000-10-10 = 10001010)
        # Because xml:ids are V(udat)1000-10-10ID
        
        if "Vudat" in xmlid: # Prefix for some xml:ids
            persid = xmlid.replace("Vudat","")
        else:
            persid = xmlid[1:] # Prefix for the rest of the xml:ids
        persid = persid.replace(datenumbers,"")
        if "-" in persid: # Indicates date range in xmlid.
            persid = persid[3:] # Remove -XX left behind.
        #print("\n")
        
        # Collect all known information in dict d
        d[xmlid]['title'] = title
        d[xmlid]['type'] = itemType
        d[xmlid]['date'] = date
        d[xmlid]['ID'] = persid
        
        #print(xmlid,title,itemType,date,"pe/orgID:",persid)
        i+=1
print(i,"total","\ndocDate elements:",docDates,"\nregular date elements:",regDates,"\nmscontentscount:",mscontentscount,"\nbibl count:",biblcount)
iP=0 # Count of persons
iO=0 # Count of organizations
found_persons = [] # Applies to both, where we have a title with a positive ID identified
print("Working...")
for item in d: # For every dict entry
    whoid = d[item]['ID'] # Get the ID
    persid = "pe"+whoid # Test for personal ID
    orgid = "org"+whoid # Test for organization ID
    try: # Try clause because attempting to use None below will throw an exception
        persdiv = registry.find('div', {'xml:id':persid}) # Test for personal ID
        name = persdiv.find('persName') # Attempt to retrieve personal name
        for match in name.findAll():
            match.unwrap() # Removes subelements
        newname = ""
        for x in name.contents: # Can't use title.contents[0]. Making new string as workaround.
            newname+=" "+x
        name = newname.strip()
        name = re.sub(' +', ' ',name)
        #print("PERS - Title:",d[item]['title'],"To:",d[item]['ID'],"Registry:",name) # Report
        iP+=1
        found_persons.append(item)
        d[item]['peID'] = "pe"+whoid
        d[item]['clearname'] = name
        # Person confirmed
    except: # If an exception is thrown, it's not a person
        try: # Test for organization ID
            orgid = registry.find('div', {'xml:id':orgid})
            name = orgid.find('item',{'rend':'name'})
            for match in name.findAll():
                match.unwrap()
            newname = ""
            for x in name.contents: # Can't use title.contents[0]. Making new string as workaround.
                newname+=" "+x
            name = newname.strip()
            name = re.sub(' +', ' ',name)
            #print("ORG - Title:",d[item]['title'],"To:",d[item]['ID'],"Registry:",name) # Report
            iO+=1
            found_persons.append(item)
            d[item]['orgID'] = "org"+whoid
            d[item]['clearname'] = name
        except: # If an exception is thrown, it's not an organization
            pass # Report or pass.

print(iP,"personal names\n",iO,"organizations")
losttitles = [] # List of items that do not have a person/organization's ID *and* is not attributed to an anon
for item in d: 
    if item not in found_persons and d[item]['ID'] != "NN":
        #print(item,"not found. Title",d[item]['title'],"ID:",d[item]['ID'])
        losttitles.append(d[item]['title'])
# Get full names and their IDs from the registry xml file
i=0
iddict = defaultdict(dict)
orgs = []
pers = []
for orgid in registry.findAll('div', {'xml:id':re.compile('org.*')}):
    name = orgid.find('item',{'rend':'name'})
    for match in name.findAll():
        match.unwrap()
    newname = ""
    for x in name.contents: # Can't use title.contents[0]... New string as workaround.
        newname+=" "+x
    newname = re.sub('\\n',"",newname)
    name = newname.strip()
    name = re.sub(' +', ' ',name)
    print(name)
    i+=1
    orgs.append(name)
    iddict[name]["ID"] = orgid['xml:id']
print(i,"organizations")
i=0
for persid in registry.findAll('div', {'xml:id':re.compile('pe.*')}):
    name = persid.find('item',{'rend':'name'})
    for match in name.findAll():
        match.unwrap()
    newname = ""
    
    for x in name.contents: # Can't use title.contents[0]... New string as workaround.
        newname+=" "+x
    name = newname
    name = re.sub('\\n',"",name)
    name = name.strip()
    name = re.sub(' +', ' ',name)
    print(name)
    i+=1
    iddict[name]["ID"] = persid['xml:id']
    pers.append(name)
print(i,"persons")
# Macerate the list of missing titles in an attempt to extract the name(s) included in each title by preposition guessing.
# This method has a success rate of, like, 75%. It's not perfect, but extracts a reasonable number of names.
# I suspect that chances of success would increase by creating a list of terms that should just be excluded entirely -
# like a stop word list - and analysing more thoroughly where each name is placed in relation to a preposition.
titlesstillmissing,nodontadd,fulltitlestillmissing = [],[],[]
v=0
for x in losttitles:
    z = x.strip()
    #print("Mod 0:",z)
    z = z.replace("Dedikasjon til","")
    z = z.replace("Hilsen til","")
    z = z.replace("Hilsener til","")
    #print("Mod 1:",z)
    if " i " in z:
        a = z.split(" i ")
    elif " på " in z:
        a = z.split(" på ")
    elif " til " in z:
        a = z.split(" til ")
    elif " bakpå " in z:
        a = z.split(" bakpå ")
    else:
        a = [z]
        #print("Neither",x)
    if "Hilsen" in a[0]:
        z = a[1]
    else:
        z = a[0]
    #print(z)
    z = z.strip()
    #print("Mod 2:",z)
    
    # Check the names that we got against the registry - organizations
    for xx in orgs:
        if z.lower() in xx.lower():
            print("Mod 3O:",x,"/",z,"/",xx)
            v+=1
            nodontadd.append(z)
            for document in d:
                #print(x)
                exists = d.get(document, {}).get('title')
                if exists == x:
                    theid = iddict.get(xx)["ID"]
                    d[document]['orgID'] = theid
                    d[document]['clearname'] = xx.strip()
                    print(x,"/",xx.strip(),exists,"updated to ID",theid)
    # Check the names that we got against the registry - persons
    for xx in pers:
        if z.lower() in xx.lower():
            #print("Mod 3P:",x,"/",z,"/",xx)
            v+=1
            nodontadd.append(z)
            for document in d:
                #print(x)
                exists = d.get(document, {}).get('title')
                if exists == x:
                    # WARNING This will populate "Hilsen til Møller på baksiden av fotografi fra Forum Romanum"
                    # "Møller" is not a good match. In future, exclude this.
                    theid = iddict.get(xx)["ID"]
                    d[document]['peID'] = theid
                    d[document]['clearname'] = xx.strip()
                    print(x,"/",xx.strip(),exists,"updated to ID",theid)
    if z not in nodontadd:
        titlesstillmissing.append(z)
        fulltitlestillmissing.append(x)
    #print("")
print(v,"new entries")
# Debug and report step. Creates fullID column in the dictionary.
i=0
for x in d:
    #print(x)
    peID = d.get(x, {}).get('peID')
    orgID = d.get(x, {}).get('orgID')
    ID = d.get(x, {}).get('ID')
    clearname = d.get(x, {}).get('clearname')
    if peID:
        i+=1
        print("PEID",x,"=",ID,"/",peID,"=",clearname)
        print(i)
        d[x]['fullID'] = peID
    elif orgID:
        i+=1
        print("ORGID",x,"=",ID,"/",orgID,"=",clearname)
        print(i)
        d[x]['fullID'] = orgID
# Token matching by Ruth. This is an additional effort to mash up titles that still haven't received a recipient.
# Uses the partial titles that were macerated based on proposition guessing earlier.

PossibleTokenMatchReg = []
LeftoverNames = []
                      
for entry in titlesstillmissing:
    string = re.sub('\(', '',(re.sub('\)', '', str(entry))))
    stringLower = string.lower()
    tokens = stringLower.split()
    TokenMatchReg = []            
    for person in pers:
        personLower = person.lower()
        personTokens = re.sub('\(', '',(re.sub('\)', '',(re.sub('\]', '',(re.sub('\[', '', personLower)))))))
    # personTokens = personTokens.split()
        
        if all(x in personTokens for x in tokens):
            index = titlesstillmissing.index(entry)
            variaID = ''
            for item in d:
                if d[item]['title'] == fulltitlestillmissing[index]:
                    variaID = item
                
            TokenMatchReg.append(variaID + ':' + fulltitlestillmissing[index] + '/' + person)
    
    for org in orgs:
        orgLower = org.lower()
        orgTokens = re.sub('\(', '',(re.sub('\)', '',(re.sub('\]', '',(re.sub('\[', '', orgLower)))))))
        
        if all(x in orgTokens for x in tokens):
            index = titlesstillmissing.index(entry)
            variaID = ''
            for item in d:
                if d[item]['title'] == fulltitlestillmissing[index]:
                    variaID = item
            TokenMatchReg.append( variaID + ':' + fulltitlestillmissing[index] + '/' + orgTokens)
        
        
    if len(TokenMatchReg) != 0:
        PossibleTokenMatchReg.append(TokenMatchReg)
    else:
            LeftoverNames.append(entry)
        
print(PossibleTokenMatchReg)
# print(LeftoverNames)
# print(len(LeftoverNames))
# Match fullnames to iddict for ID
# Create list for inexact matches
idsfound,ambignames,ambigids,ambig,ambigdocs=[],[],[],[],[]
for x in PossibleTokenMatchReg:
    for y in x:
        z = y.split(":")
        docID = z[0]
        names = z[1].split("/")
        name = names[1]
        name = name.strip()
        if docID in idsfound:
            print("-AMBIGUOUS:",docID,name,iddict[name]['ID'])
            ambig.append(docID)
        else:
            #print(docID,name)
            idsfound.append(docID)
for x in PossibleTokenMatchReg:
    for y in x:
        z = y.split(":")
        docID = z[0]
        names = z[1].split("/")
        name = names[1]
        name = name.strip()
        if docID not in ambig:
            print("Match for",docID,name,iddict[name]['ID'])
            d[docID]['fullID'] = iddict[name]['ID']
            d[docID]['clearname'] = name
        else: # Really I'd just skip this and commit them to a list/file
            ambigdocs.append(docID)
            ambignames.append(name)
            ambigids.append(iddict[name]['ID'])
df = pd.DataFrame.from_dict(d).fillna("N/A").T
df = df.drop(['peID', 'orgID'], axis=1)
df.to_csv("varia_file.csv", sep=',', encoding='utf-8',index=True)
# What's going on with the ambigs, then?
i=0
while i<len(ambigdocs):
    print(ambigdocs[i],ambignames[i],ambigids[i])
    i+=1
i=0
for x in df['fullID']:
    if x != "N/A":
        i+=1
print(i,"entries have IDs")
i=0
for x in df['ID']:
    i+=1
print(i,"entries")