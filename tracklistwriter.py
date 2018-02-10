import string, codecs, types, re
from collections import OrderedDict

TracklistFilename = "tracklist-in.txt"
SettingsFilename = "settings.txt"
OutFilename = "tracklist-out.txt"

def parse_tracklist_file(tracklist_path):
    tListFile = codecs.open(tracklist_path, encoding='utf-8-sig')
    allLines = [ line for line in tListFile.readlines() ]
    return parse_tracklist_list(allLines)

def parse_tracklist_str(tracklist_str):
    allLines = [ line for line in tracklist_str.split("\n") ]
    return parse_tracklist_list(allLines)

def parse_tracklist_list(tracklist_list):
    allLines = [ line.rstrip() for line in tracklist_list ]
    tlines = []
    for line in allLines:
        if len(line) == 0:
            continue
        tlines.append(line)

    return tlines

def parse_settings_file(settings_path):
    settingsFile = codecs.open(settings_path, encoding='utf-8')
    allLines = [ line.rstrip("\r\n") for line in settingsFile.readlines() ]
    slines = []
    wlines = []
    addingWorks = False #For adding classical works

    #Set up lines of settings and lines of classical works:
    for n in range(len(allLines)):
        spaceFind = re.search(ur"^\s+$", allLines[n], re.M|re.U)
        if not spaceFind:
            if len(allLines[n]) == 0 or allLines[n][0] == '#':
                continue
            if "Begin_adding_next_line" in allLines[n]:
                addingWorks = True
            elif addingWorks:
                wline = allLines[n].split()
                if wline[0][0] == '[':
                    wline.insert(0, u"p") #inserts placeholder, which will be resolved in WriteClassical
                wlines.append(wline)
            else:
                slines.append(allLines[n])

    settings = {}
    sourceFind = re.search(u'^Source:(\s*)(.*)$', slines[0], re.U|re.I)
    if sourceFind:
        if "mazon" in sourceFind.group(2): settings["source"] = 'z'
        else: settings["source"] = sourceFind.group(2)[0].lower()
    if settings["source"] == 'o': #Other source may want to specify phrases to clear from raw input
        settings["toClear"] = []
        while "Is_VA:" not in slines[1]:
            if slines[1][:2] == u"@@" or slines[1][-2:] == u"@@":
                settings["toClear"].append((string.replace(slines[1], u"@@", u"", 1), "line"))
            elif slines[1][:2] == u"!@" and slines[1][-2:] == u"!@":
                settings["toClear"].append((slines[1][2:-2], "headtail"))
            elif slines[1][:2] == u"!@":
                settings["toClear"].append((slines[1][2:], "head"))
            elif slines[1][-2:] == u"!@":
                settings["toClear"].append((slines[1][:-2], "tail"))
            else:
                settings["toClear"].append((slines[1], "exact"))
            del slines[1]


    vaFind = re.search(u'^Is_VA:(\s*)(.*)$', slines[1], re.U|re.I)
    if vaFind: settings["va"] = vaFind.group(2).lower()

    langFind = re.search(u'^Language:(\s*)(.*)$', slines[2], re.U|re.I)
    if langFind:
        splitLangs = langFind.group(2).split()
        settings["lang"] = splitLangs[0][0].lower()
        if len(splitLangs) > 1:
            settings["mvlang"] = splitLangs[1][0].lower() #Optional language for movements (e.g. Italian)
        else: settings["mvlang"] = settings["lang"]

    mergeFind = re.search(u'^Merge:(\s*)(.*)$', slines[3], re.U|re.I)
    if mergeFind: settings["merge"] = mergeFind.group(2)[0].lower()

    settings["isClass"] = False
    if len(wlines) > 0:
        settings["isClass"] = True
        settings["wlines"] = wlines #The lines are unchanged until WriteClassical

    return settings

def TrackListWrite(tracklist, settings):
    #Take in tracklist and settings files and separate lines:
    tlines = tracklist

    global global_settings
    global_settings = settings

    #Check source and run corresponding function:
    if settings["source"] == 'd':
        return DiscogsWrite(tlines)
    elif settings["source"] == 'i':
        return iTunesWrite(tlines)
    elif settings["source"] == 'z':
        return AmazonWrite(tlines)
    elif settings["source"] == 'a':
        return AllMusicWrite(tlines)
    elif settings["source"] == 'o':
        return OtherWrite(tlines)
    elif settings["source"] == 'r':
        return RYMWrite(tlines)
    else:
        raise ValueError("This source isn't supported yet!")


def DiscogsWrite(tlines):
    # out = open(output, 'w')
    if ("Tracklist" in tlines[0]) or (" Credits" in tlines[0]):
        del tlines[0] #Just in case you paste it in (script might think it's a disc title or something)

    toWrite = []

    #-------Main loop: begins with the last line and counts down (for a few reasons)--------
    for i in range(len(tlines)-1,-1,-1):
        string.replace(tlines[i], '|', '/') #Since | characters are meta-chars in RYM tracklist
        mainTrack = None #Must be reset each iteration
        mainAppend = None #^^^
        dontWrite = False

        #In rare cases, a CD track may be entered in the form 0:00:00, when it should be 00:00
        longTrack = re.search(r'(\d+):(\d+):(\d+)$', tlines[i], re.M|re.U)
        if longTrack:
            newDur = FixLongTrack(longTrack.group(1), longTrack.group(2), longTrack.group(3))
            tlines[i] = string.replace(tlines[i], str(longTrack.group()), newDur)

        #Search for track info:
        trackInfo = re.search(r'^(\d+[\.]?[\d\w]*)-?(\d*\.?[\d\w]*)\s*\t+(.+)\s*\t+(\d+:\d+)$', tlines[i], re.M|re.U)
        if not trackInfo: trackInfo = re.search(r'^([A-Z])-?(\d*\.?[\d\w]*)\s*\t+(.+)\s*\t+(\d+:\d+)$', tlines[i], re.M|re.U)
        #Keep searching, this time without capturing track durations:
        if not trackInfo: trackInfo = re.search(r'^(\d+\.?[\d\w]*)-?(\d*\.?[\d\w]*)\s?\t+(.+)\s*$', tlines[i], re.M|re.U)
        if not trackInfo: trackInfo = re.search(r'^([A-Z])-?(\d*\.?[\d\w]*(?:ix|iv|v?i{0,3}|IX|IV|V?I{0,3}))\s?\t+(.+)\s*$', tlines[i], re.M|re.U)

        #^ More strict subtrack finding here to prevent errors

        if trackInfo:
            #Preparing data to write to track (might be modified later in script):
            trTitle = trackInfo.group(3)
            trArtist = u''
            titleInfo = re.search(ur'\u2013(.+)\t(.+)$', trTitle, re.M|re.U) #For VA releases
            #Need to split tabbed entries if they exist:
            if titleInfo:
                if global_settings["va"] == 'y':
                    trArtist = StripSpaces(titleInfo.group(1)) #Will only use if it's a V/A release
                    if trArtist[-1] == '*': trArtist = trArtist[:-1] #Get rid of asterisk at end of artist name
                    isDisambig = re.search(ur'(.+) \(\d+\)$', trArtist, re.M|re.U) #Disamiguated artist names are appended with (#)
                    if isDisambig:
                        trArtist = isDisambig.group(1) + u' - '
                    else:
                        trArtist = trArtist+ u' - '
                trTitle = StripSpaces(titleInfo.group(2))

            #Now Format the title:
            trTitle = CapsFormat(StripSpaces(trTitle))

            try: #Duration not always listed, esp. for vinyl and tape
                trHead = trackInfo.group(4)[:-3] #Hrs and mins
                trTail = trackInfo.group(4)[-3:] #Seconds
                trLen = StripLead0(trHead) + trTail
            except:
                trLen = ""
            if trackInfo.group(2):
                discNum = StripLead0(trackInfo.group(1))
                #CDs need dots between disc and track number:
                if discNum not in string.ascii_uppercase:
                    discNum = discNum + '.'
                trNum = StripLead0(trackInfo.group(2))
            else:
                num = StripLead0(trackInfo.group(1))

            #Determine if track is a sub-track (in discogs, they're denoted by periods: 2-01.1, 1.a, etc)
            #... if found, delete tracknum field, and put alphanumeric in tracktitle field:
            for g in [1, 2]: #Only look at track and disc field from trackInfo:
                if not trackInfo.group(g):
                    continue
                subTrack = re.search(r'(.*)\.(.*)', trackInfo.group(g), re.M|re.U)
                if not subTrack: #might be a subtrack if form is 4a, 1-6B, Bc, etc.
                    subTrack = re.search(r'^(.*[\dA-Z])([a-zA-Z])$', trackInfo.group(g), re.M|re.U)
                if subTrack:
                    tempArtist = trArtist #to prevent errors in subtrack naming
                    trArtist = u"" #erase artist info for now
                    tempTr = subTrack.group(1) #For later, if / when main track is found
                    subNum = subTrack.group(2) #subNum must be alphanumeric to work
                    try:
                        if global_settings["isClass"]:
                            subNum = ToRoman(int(subNum))
                        else:
                            subNum = ToAlpha(int(subNum)-1)
                    except:
                        subNum = subNum.lower()

                    #Make sure main track is present and listed above sub-tracks. If not, make a placeholder.
                    #Credits have been cleared, so they shouldn't be a problem
                    if subNum == 'a' or subNum == 'i' and toWrite[-1][1:3] == 'ii': #Assumes first sub-track is part a, or maybe roman numerals
                        if tlines[i] == 0:
                            #There can't be a main track if the movement is on the first line:
                            mainTrack = u''
                        else: #Check line before and see if it's a not a normal track:
                            isNormTrack = re.search(r'^(\d+\.?[\d\w]*)-?(\d*\.?[\d\w]*)\t+(.+)$', tlines[i-1], re.M|re.U)
                            if not isNormTrack: isNormTrack = re.search(r'^([A-Z])-?(\d*\.?[\d\w]*(?:((xc|x?l|l?x{1,3})(ix|iv|v?i{0,3})|(xc|xl|l?x{0,3})(ix|i?v|v?i{1,3}))|((XC|X?L|L?X{1,3})(IX|IV|V?I{0,3})|(XC|XL|L?X{0,3})(IX|I?V|V?I{1,3}))))\t+(.+)$', tlines[i-1], re.M|re.U)
                            if not isNormTrack:
                                mainTrack = u'' + string.replace(tlines[i-1], ur'\t', u'')
                            else:
                                mainTrack = u''

                    #Now we must prepare a main track if it's been found (it's set to None each iteration):
                    if mainTrack != None:
                        #Format main track title
                        mainTrack = CapsFormat(mainTrack)
                        mainInfo = re.search(ur'^(.+)\((\d+):(\d+)\)$', mainTrack, re.M|re.U)
                        if mainInfo:
                            mainHead = mainInfo.group(2) #Hrs and mins
                            mainTail = mainInfo.group(3) #Seconds
                            mainLen = StripLead0(mainHead) + ':' + mainTail
                            mainTrack = mainInfo.group(1)
                            #If main track length exists, then we need to clear track lengths for subtracks:
                            trLen = u''
                            erasingLengths = True
                            while erasingLengths:
                                for line in range(len(toWrite)):
                                    if toWrite[line][0] == u'|': #Subtracks always start with |
                                        toWrite[line] = re.sub(ur'\d+:\d+$', u'', toWrite[line], 1, re.M|re.U)
                                    else:
                                        erasingLengths = False #Erase only up until last subtrack
                                erasingLengths = False
                        #Check if merging subtracks is on:
                        if global_settings["merge"] == 'y':
                            dontWrite = True #Don't write the current subtrack
                            marked = []
                            if len(mainTrack) > 1:
                                mainTrack = mainTrack + ': ' + trTitle
                            else:
                                mainTrack = trTitle
                            mainTrack = trTitle
                            for p in range(len(toWrite)-1, -1, -1):
                                subSearch = re.search(ur'^\|\w+\.\s(.*)\|', toWrite[p], re.M|re.U) #finds subtracks
                                if subSearch:
                                    lenSearch = re.search(ur'\|.*\|(\d+:\d+)', toWrite[p], re.M|re.U) #finds subtrack trlengths
                                    if lenSearch: #merge track lengths together:
                                        trLen = AddDurations(trLen, lenSearch.group(1))
                                    mainTrack = mainTrack + "; " + subSearch.group(1)
                                    marked.append(p)
                                else:
                                    break
                            if len(marked) > 0:
                                for m in marked:
                                    del toWrite[m]
                        #Assumes subtracks are by the same artist, otherwise things get messy:
                        mainTrack = tempArtist + mainTrack

                        try:
                            #We'll add this later:
                            mainAppend = discNum + tempTr + '|' + mainTrack + '|' + mainLen
                        except:
                            try:
                                mainAppend = discNum + tempTr + '|' + mainTrack + '|' + trLen
                            except:
                                try:
                                    mainAppend = num + tempTr + '|' + mainTrack + '|' + mainLen
                                except:
                                    mainAppend = num + tempTr + '|' + mainTrack + '|' + trLen


                    #Now remove track number, and insert subNum into track title if subtrack:
                    if trackInfo.group(2):
                        discNum = ""
                        trNum = ""
                    else:
                        num = ""
                    trTitle = subNum + ". " + trTitle

            #May want to lookup artist shortcut in the future for VA, although this could lead to problems...

            #Write actual lines after all modifications:
            if not dontWrite:
                if trackInfo.group(2):
                    toWrite.append(discNum + trNum + '|' + trArtist + trTitle + '|' + trLen)
                else:
                    toWrite.append(num + '|' + trArtist + trTitle + '|' + trLen)
            if mainAppend: #write main track after last sub-track:
                toWrite.append(mainAppend)

        #If trackInfo was not found:
        else:
            #Perhaps it is the title of a disc, a classical main_work, or some other title, but not a suite (Those have been moved to tracks):
            nonTrack = re.sub(ur"^\t", u"", tlines[i], 0, re.M|re.U)
            nonTrack = re.sub(ur"\t.*", u"", nonTrack, 0, re.M|re.U)
            if nonTrack == u'-': #Discogs notation for: The following tracks don't belong under the last title
                #RYM does not need this
                del tlines[i]
                continue
            isMainTitle = True #Assume we have found a main track until proven otherwise
            #If there was a suite, it is the most recently added line:
            try:
                nonTrack = re.sub(ur'\(\s\d+:\d+\)$', u'', nonTrack)
                lastTrackWritten = re.search(ur'\|(.+)\(\d+:\d+\)\|', toWrite[-1], re.M|re.U) #Extract title info from last line
                if not lastTrackWritten: lastTrackWritten = re.search(ur'\|(.+)\|', toWrite[-1], re.M|re.U) #Might not have a length
                lastTrack = CapsFormat(lastTrackWritten.group(1))
                nonTrack = CapsFormat(nonTrack)
                if nonTrack == lastTrack: #Must match title info of last track
                    isMainTitle = False
                if isMainTitle:
                    nonTrack = CapsFormat(nonTrack)
                    #We can write main titles immediately(?):
                    mainForm = '|[b]' + nonTrack + '[/b]|'
                    toWrite.append(mainForm)
            except:
                pass

    #------------End of main loop-------------

    toWrite.reverse()

    #Finally, insert links to classical works where applicable:
    if global_settings["isClass"]:
        toWrite = WriteClassical(toWrite)

    # print "------------------------"
    # print "Results written to txt:"
    # print "------------------------"
    # print ""
    # for line in toWrite:
    #     print line
    #
    # #Actual text writing:
    # for line in toWrite:
    #     out.write(line.encode('utf-8') + "\n")
    # out.close()

    return toWrite


def iTunesWrite(tlines):
    # out = open(output, 'w')
    #If heading line "Name, Artist, Price [etc]" was copied, throw it out:
    tabFirstLine = re.search(ur"\t", tlines[0], re.M|re.U)
    if tabFirstLine: del tlines[0]
    #If last line "## Songs" was copied, throw it out:
    tabLastLine = re.search(ur"\t", tlines[-1], re.M|re.U)
    if tabLastLine: del tlines[-1]

    toWrite = []
    #Set up lists to store track info:
    trNumL = [] #List of ints
    trDiscL = [] #List of unicode: u"#."
    trTitleL = []
    trArtistL = []
    trDurL = []
    IsMultiDisc = False
    OnDisc = 1

    #Main loop: Just goes forward through each line.
    for i in range(len(tlines)):
        #First line is just track number:
        trackFound = re.search(ur"^(\d+)$", tlines[i], re.M|re.U)
        if trackFound:
            #Append new values to lists:
            trNumL.append(int(trackFound.group(1)))
            trTitleL.append(u"")
            trArtistL.append(u"")
            trDurL.append(u"")
            trDiscL.append(str(OnDisc) + u".")
            #Next line is track title:
            trTitle = CapsFormat(tlines[i+1])
            trTitleL[-1] = trTitle
            if global_settings["va"] == 'y': #Only save track artist if VA release
                trArtist = tlines[i+2] + u" - "
                trArtistL[-1] = trArtist
            #Next line is duration:
            longTrack = re.search(r'(\d+):(\d+):(\d+)', tlines[i+3], re.M|re.U)
            if longTrack:
                trDurL[-1] = FixLongTrack(longTrack.group(1), longTrack.group(2), longTrack.group(3))
            elif tlines[i+3] == u'--': #Indicates main work
                trTitleL[-1] = u'[b]' + trTitleL[-1] + u'[/b]'
                trNumL[-1] = u""
                trDiscL[-1] = u""
            else: trDurL[-1] = tlines[i+3]
            #Now determine disc numbers:
            if trNumL[-1] == u"": pass
            elif len(trNumL) > 1:
                if trNumL[-2] == u"":
                    if len(trNumL) == 2: pass
                    elif int(trNumL[-1]) <= int(trNumL[-3]):
                        #Found a reset in track numbers. Start new disc
                        IsMultiDisc = True
                        OnDisc += 1
                        trDiscL[-1] = str(OnDisc) + u"."
                else:
                    if int(trNumL[-1]) <= int(trNumL[-2]):
                        IsMultiDisc = True
                        OnDisc += 1
                        trDiscL[-1] = str(OnDisc) + u"."
            try:
                i += 6
            except:
                break
    #End of main loop.
    if not IsMultiDisc: #Erase discnum info
        for e in range(len(trDiscL)): trDiscL[e] = u""
    #Make each line in RYM format:
    for x in range(len(trNumL)):
        toWrite.append(trDiscL[x] + str(trNumL[x]) + u'|' + trArtistL[x] + trTitleL[x] + '|' + trDurL[x])

    #Finally, insert links to classical works where applicable:
    if global_settings["isClass"]:
        toWrite = WriteClassical(toWrite)

    # print "------------------------"
    # print "Results written to txt:"
    # print "------------------------"
    # print ""
    # for line in toWrite:
    #     print line
    #
    # #Actual text writing:
    # for line in toWrite:
    #     out.write(line.encode('utf-8') + "\n")
    # out.close()

    return toWrite

def AmazonWrite(tlines):
    # out = open(output, 'w')
    if "Sample this album" in tlines[0]: del tlines[0]
    toWrite = []
    #Set up lists to store track info:
    trNumL = [] #List of ints
    trDiscL = [] #List of unicode: u"#."
    trTitleL = []
    trArtistL = []
    trDurL = []
    trWorkL = [] #For saving work names
    worksToWrite = [] #For writing main works as titles
    IsMultiDisc = False
    OnDisc = 1
    #Main loop: Just goes forward through each line.
    for i in range(len(tlines)):
        #First see if a new disc has started:
        discFound = re.search(ur"Disc (\d+)", tlines[i], re.M|re.U)
        if discFound: #Amazon, unlike iTunes, indicates new discs:
            OnDisc = discFound.group(1)
            IsMultiDisc = True
            continue
        #First line is just track number:
        trackFound = re.search(ur"^(\d+)\t*$", tlines[i], re.M|re.U)
        if trackFound:
            #Append new values to lists:
            trNumL.append(trackFound.group(1))
            trTitleL.append(u"")
            trArtistL.append(u"")
            trDurL.append(u"")
            trWorkL.append(u"")
            trDiscL.append(str(OnDisc) + u".")
            #Next line is track title:
            #Separate out classical work if possible:
            if global_settings["isClass"]:
                #Format is rather strict, but is often used on Amazon
                classFind = re.search(ur"(?:\: )(.+?)(?:\: )(\d+|((xc|x?l|l?x{1,3})(ix|iv|v?i{0,3})|(xc|xl|l?x{0,3})(ix|i?v|v?i{1,3})))(\. .+)$", tlines[i+1], re.M|re.U|re.I)
                if not classFind: classFind = re.search(ur"^(.+?)(?:\: )(\d+|((xc|x?l|l?x{1,3})(ix|iv|v?i{0,3})|(xc|xl|l?x{0,3})(ix|i?v|v?i{1,3})))(\. .+)$",  tlines[i+1], re.M|re.U|re.I)
                if classFind:
                    trWork = CapsFormat(classFind.group(1))
                    trWorkL[-1] = trWork
                    trTitle = CapsFormat(classFind.group(2) + classFind.group(8))
                    trTitleL[-1] = trTitle
                    if len(trWorkL) == 1 or trWorkL[-1] != trWorkL[-2]:
                        #Insert info into second-to-last list element
                        trNumL.insert(-1, u"")
                        trTitleL.insert(-1, '[b]' + trWork + '[/b]')
                        trArtistL.insert(-1, u"")
                        trDurL.insert(-1, u"")
                        trDiscL.insert(-1, u"")
                else:
                    trTitle = CapsFormat(tlines[i+1])
                    trTitleL[-1] = trTitle
            else:
                trTitle = CapsFormat(tlines[i+1])
                trTitleL[-1] = trTitle
            #Now determine whether track artist is present:
            if tlines[i+2][:3] == u"by ":
                if global_settings["va"] == 'y': #Only save track artist if VA release
                    trArtist = tlines[i+2][3:] + u" - "
                    trArtistL[-1] = trArtist
                i += 1 #go forward a line, since this line is optional
            #Next line is duration and maybe price "Album Only":
            longTrack = re.search(ur'^(\d+):(\d+):(\d+)', tlines[i+2], re.M|re.U)
            if longTrack: tlines[i+2] = re.sub(ur'^\d+:\d+:\d+', FixLongTrack(longTrack.group(1), longTrack.group(2), longTrack.group(3)), tlines[i+2], 1, re.M|re.U)
            #May contain "Album Only"
            aoFound = re.search(ur"(\d+:\d+)\t+Album", tlines[i+2], re.M|re.U)
            if aoFound:
                trDurL[-1] = aoFound.group(1)
                try: i += 3 #No price line
                except: break
            else:
                trDurL[-1] = tlines[i+2]
                try: i += 4 #Price line
                except: break

    #End of main loop.
    if not IsMultiDisc: #Erase discnum info
        for e in range(len(trDiscL)): trDiscL[e] = u""
    #Make each line in RYM format:
    for x in range(len(trNumL)):
        toWrite.append(trDiscL[x] + trNumL[x] + u'|' + trArtistL[x] + trTitleL[x] + '|' + trDurL[x])
    #Insert any classical main works:
    for y in range(len(worksToWrite)-1,-1,-1):
        toWrite.insert(worksToWrite[y][0], worksToWrite[y][1])

    #Finally, insert links to classical works where applicable:
    if global_settings["isClass"]:
        toWrite = WriteClassical(toWrite)

    # print "------------------------"
    # print "Results written to txt:"
    # print "------------------------"
    # print ""
    # for line in toWrite:
    #     print line
    #
    # #Actual text writing:
    # for line in toWrite:
    #     out.write(line.encode('utf-8') + "\n")
    # out.close()

    return toWrite

def AllMusicWrite(tlines):
    # out = open(output, 'w')
    #I hate AllMusic, but extracting info from it is simple enough. Similar to Amazon and iTunes
    if " Listing" in tlines[0]: del tlines[0]
    if "\tTime" in tlines[0]: del tlines[0]
    if "blue highl" in tlines[-1]: del tlines[-1]

    toWrite = []
    #Set up lists to store track info:
    trNumL = [] #List of ints
    trDiscL = [] #List of unicode: u"#."
    trTitleL = []
    trArtistL = []
    trDurL = []
    IsMultiDisc = False
    OnDisc = 1
    i = 0
    while i < len(tlines):
        #First see if new disc has started:
        newDisc = re.search(ur"Track Listing - Disc (\d+)", tlines[i], re.M|re.U)
        if newDisc:
            IsMultiDisc = True
            OnDisc = int(newDisc.group(1))
            i += 2 #Skip next line, which is always filler line
        #First line is track no.:
        trackFound = re.search(ur"^(\d+)\t*$", tlines[i], re.M|re.U)
        if trackFound:
            #Append new values to lists:
            trNumL.append(trackFound.group(1))
            #track title is always next line:
            trTitleL.append(CapsFormat(tlines[i+1]))
            trArtistL.append(u"")
            trDurL.append(u"")
            trDiscL.append(str(OnDisc) + u".")
            j = 2 #start two lines down to look for track duration:
            nextIt = 0 #to be reset later
            while True:
                #If loop reaches next trackno, the duration is not there:
                trNumFind = re.search(ur"^\d+\t*$", tlines[i+j], re.M|re.U)
                if trNumFind:
                    nextIt = j #So that next iteration starts on track no.
                    break
                longTrack = re.search(ur"^(\d+)\:(\d+)\:(\d+)(?:$|\s+Spotify|\s+Amazon)$", tlines[i+j], re.M|re.U)
                if longTrack: tlines[i+j] = re.sub(ur'^\d+:\d+:\d+', FixLongTrack(longTrack.group(1), longTrack.group(2), longTrack.group(3)), tlines[i+j], 1, re.M|re.U)
                durFind = re.search(ur"^(\d+\:\d+)(?:\s*Spotify|\s*Amazon|\s*SpotifyAmazon)?$", tlines[i+j], re.M|re.U)
                if durFind:
                    nextIt = j+1 #So that next iteration starts on track no.
                    trDurL[-1] = durFind.group(1)
                    break
                else: j += 1
                if i+j == len(tlines):
                    break
            #Now find track artist if applicable:
            if global_settings["va"] == 'y': #Only save track artist if VA release
                #"feat:" lines should be ignored (put in credits section?)
                featSearch = re.search(ur"^feat\:\s+.+", tlines[i+j-1], re.M|re.U)
                if featSearch: trArtistL[-1] = tlines[i+j-2] + u" - "
                else: trArtistL[-1] = tlines[i+j-1] + u" - "
        else:
            #AllMusic puts work title in separate line immediately before
            trNumL.append(u"")
            trArtistL.append(u"")
            trDurL.append(u"")
            trDiscL.append(u"")
            trTitleL.append(u"[b]" + StripSpaces(tlines[i]) + u"[/b]")
            nextIt = 1
        #Now determine where next iteration will be.
        if nextIt > 0: i += nextIt
        else: break
    #End of main loop.
    if not IsMultiDisc: #Erase discnum info
        for e in range(len(trDiscL)): trDiscL[e] = u""
    #Make each line in RYM format:
    for x in range(len(trNumL)):
        toWrite.append(trDiscL[x] + trNumL[x] + u'|' + trArtistL[x] + trTitleL[x] + '|' + trDurL[x])


    #Write classical:
    if global_settings["isClass"]:
        toWrite = WriteClassical(toWrite)

    # print "------------------------"
    # print "Results written to txt:"
    # print "------------------------"
    # print ""
    # for line in toWrite:
    #     print line
    #
    # #Actual text writing:
    # for line in toWrite:
    #     out.write(line.encode('utf-8') + "\n")
    # out.close()

    return toWrite

def RYMWrite(tlines):
    # out = open(output, 'w')
    #This one is easy: just format title if needed, and insert classical works.
    toWrite = []
    for t in range(len(tlines)):
        titleFind = re.search(ur"\|(.+)\|", tlines[t], re.M|re.U)
        if titleFind:
            linkFind = re.search(ur"\|.*(\[Work\d+,|\[Artist\d+,|\[Album\d+,).+\].*\|.*", tlines[t], 0)
            if linkFind:
                tlines[t] = re.sub(ur"(.*\|)(.*)(\[Work\d+,|\[Album\d+,)(.+)(\])(.*)(\|.*)", WorkSub, tlines[t], 0, re.M|re.U)
                tlines[t] = re.sub(ur"(.*\|)(.*)(\[Artist\d+,)(.+)(\])(.*)(\|.*)", ArtistSub, tlines[t], 0, re.M|re.U)
            else:
                bracketSearch = re.search(ur".*\|.*\[.+\].*\|.*", tlines[t], re.M|re.U)
                if bracketSearch:
                    tlines[t] = re.sub(ur"(.*\|)(.*)(\[.+\])(.*)(\|.*)", BracketSub, tlines[t], 0, re.M|re.U)
                else:
                    tlines[t] = re.sub(ur"(.*\|)(.*)(\|.*)", NormalSub, tlines[t], 0, re.M|re.U)
            toWrite.append(tlines[t])


    #Write classical:
    if global_settings["isClass"]:
        toWrite = WriteClassical(toWrite)

    # print "------------------------"
    # print "Results written to txt:"
    # print "------------------------"
    # print ""
    # for line in toWrite:
    #     print line
    #
    # #Actual text writing:
    # for line in toWrite:
    #     out.write(line.encode('utf-8') + "\n")
    # out.close()

    return toWrite

def WorkSub(match):
    return match.group(1) + CapsFormat(match.group(2)) + match.group(3) + CapsFormat(match.group(4)) + match.group(5) + CapsFormat(match.group(6)) + match.group(7)

def ArtistSub(match):
    return match.group(1) + CapsFormat(match.group(2)) + match.group(3) + match.group(4) + match.group(5) + CapsFormat(match.group(6)) + match.group(7)

def BracketSub(match):
    return match.group(1) + CapsFormat(match.group(2)) + match.group(3) + CapsFormat(match.group(4)) + match.group(5)

def NormalSub(match):
    return match.group(1) + CapsFormat(match.group(2)) + match.group(3)

def OtherWrite(tlines):
    # out = open(output, 'w')
    #First find extra info in tlines and clear it:
    if len(global_settings["toClear"]) > 0:
        markForDel = []
        for t in range(len(tlines)):
            for dline in global_settings["toClear"]:
                if dline[0] in tlines[t]:
                    if dline[1] == "line":
                        markForDel.append(t)
                    elif dline[1] == "headtail":
                        tlines[t] = re.sub(ur"\S*" + dline[0] + ur"\S*", u"", tlines[t], 0, re.M|re.U)
                    elif dline[1] == "head":
                        tlines[t] = re.sub(ur"\S*" + dline[0], u"", tlines[t], 0, re.M|re.U)
                    elif dline[1] == "tail":
                        tlines[t] = re.sub(dline[0] + ur"\S*", u"", tlines[t], 0, re.M|re.U)
                    elif dline[1] == "exact":
                        tlines[t] = re.sub(dline[0], u"", tlines[t], 0, re.M|re.U)
        for e in range(len(markForDel)-1, -1, -1):
            del tlines[markForDel[e]]

    #First, fix long tracks (won't need to do this again)
    for i in range(len(tlines)):
        longTrack = re.search(ur'(\d+):(\d+):(\d+)', tlines[i], re.M|re.U)
        if longTrack: tlines[i] = re.sub(ur'\d+:\d+:\d+', FixLongTrack(longTrack.group(1), longTrack.group(2), longTrack.group(3)), tlines[i], 1, re.M|re.U)

    toWrite = []
    #There will be many search loops here, each more lenient than the last.
    #Using this method assumes all track data is written in the same format throughout.
    #Most strict is of the form "1-1. Title 1:00". Period is optional, dash can be period, and any number of spaces/tabs can separate info fields,
    #...and any non-alphanumeric can surround trackno or duration.
    if len(toWrite) == 0: #Always true, just here for consistency
        Reg1a = ur"^\b(\d+)[\-\.]?(\d*)\.?\s+(\S.*)\s+\b(\d+):(\d{1,2})\b"
        toWrite = RegByLine(Reg1a, tlines, 1, 2, 3, 4, 5)
    if len(toWrite) == 0: #If info is on separate lines, must combine all lines to search
        Reg1b = ur"^\b(\d+)[\-\.]?(?:\r\n)?(\d*)\.?(?:\r\n|\s+)\s?(\S.*)(?:\r\n)?\s*\b(\d+):(\d{1,2})\b"
        toWrite = RegOneLine(Reg1b, tlines, 1, 2, 3, 4, 5)

    #Less strict search: allow other duration formats, permit strict vinyl ("A1" not "A")
    if len(toWrite) == 0:
        Reg2a = ur"^\b([A-Z]\d+|\d+(?:[\-\.]?))(\d*)\.?\s+(\S.*)\s+\b(\d+)[:'m](\d{1,2})[s\"]?\b"
        toWrite = RegByLine(Reg2a, tlines, 1, 2, 3, 4, 5)
    if len(toWrite) == 0:
        Reg2b = ur"^\b([A-Z]\d+|\d+(?:[\-\.]?))(?:\r\n)?(\d*)\.?(?:\r\n|\s+)\s?(\S.*)(?:\r\n)?\s*\b(\d+)[:'m](\d{1,2})[s\"]?\b"
        toWrite = RegOneLine(Reg2b, tlines, 1, 2, 3, 4, 5)

    #Allow trackno to start anywhere
    if len(toWrite) == 0:
        Reg3a = ur"\b(\d+)[\-\.]?(\d*)\.?\s+(\S.*)\s+\b(\d+)[:'m](\d{1,2})[s\"]?\b"
        toWrite = RegByLine(Reg3a, tlines, 1, 2, 3, 4, 5)
    if len(toWrite) == 0:
        Reg3b = ur"\b(\d+)[\-\.]?(?:\r\n)?(\d*)\.?(?:\r\n|\s+)\s?(\S.*)(?:\r\n)?\s*\b(\d+)[:'m](\d{1,2})[m\"]?\b"
        toWrite = RegOneLine(Reg3b, tlines, 1, 2, 3, 4, 5)

    #Remaining, less complete tracklistings:
    if len(toWrite) == 0: #No trackno. Just title and duration:
        Reg000 = ur"(.+)\s+\b(\d)[:'m](\d{1,2})[s\"]?\b"
        toWrite = RegByLine(Reg000, tlines, 0, 0, 1, 2, 3)
    if len(toWrite) == 0: #No duration. Just trackno and title:
        Reg00 = ur"(\d+)\s+(.+)"
        toWrite = RegByLine(Reg00, tlines, 1, 0, 2, 0, 0)
    if len(toWrite) == 0: #Maybe it's just the title...
        Reg0 = ur"(.+)"
        toWrite = RegByLine(Reg0, tlines, 0, 0, 1, 0, 0)

    #Finally, insert links to classical works where applicable:
    if global_settings["isClass"]:
        toWrite = WriteClassical(toWrite)

    # print "------------------------"
    # print "Results written to txt:"
    # print "------------------------"
    # print ""
    # for line in toWrite:
    #     print line
    #
    # #Actual text writing:
    # for line in toWrite:
    #     out.write(line.encode('utf-8') + "\n")
    # out.close()

    return toWrite

def RegByLine(pattern, tlines, discG, tnumG, titleG, minG, secG):
    '''
    For use with "Other" sources. Looks for track data using "pattern" and writes info for each track
    based on ints discG, tnumG, titleG, minG and secG. Assumes all info can be found on one line.
    A zero (0) can be entered for any group G that won't be matched.
    '''
    toWrite = []
    for i in range(len(tlines)):
        trackInfo = re.search(pattern, tlines[i], re.M|re.U)
        if trackInfo:
            if tnumG > 0: trNum = trackInfo.group(tnumG)
            else: trNum = u""
            if discG > 0: trDisc = trackInfo.group(discG)
            else: trDisc = u""
            trTitle = CapsFormat(trackInfo.group(titleG))
            if minG > 0: trMin = StripLead0(trackInfo.group(minG)) + u":"
            else: trMin = u""
            if secG > 0: trSec = trackInfo.group(secG)
            else: trSec = u""
            if isInt(trDisc) and len(trNum) > 0: #Non-vinyl disc:
                toWrite.append(trDisc + '.' + trNum + '|' + StripSpaces(trTitle) + '|' + trMin + trSec)
            else:
                toWrite.append(trDisc + trNum + '|' + StripSpaces(trTitle) + '|' + trMin + trSec)
    return toWrite

def RegOneLine(pattern, tlines, discG, tnumG, titleG, minG, secG):
    '''
    For use with "Other" sources. Looks for track data using "pattern" and writes info for each track
    based on ints discG, tnumG, titleG, minG and secG. Looks at all lines at once.
    A zero (0) can be entered for any group G that won't be matched.
    '''
    oneline = u"\r\n".join(tlines)
    toWrite = []
    trackInfo = re.search(pattern, oneline, re.M|re.U)
    if trackInfo:
        while trackInfo:
            if tnumG > 0: trNum = trackInfo.group(tnumG)
            else: trNum = u""
            if discG > 0: trDisc = trackInfo.group(discG)
            else: trDisc = u""
            trTitle = CapsFormat(trackInfo.group(titleG))
            if minG > 0: trMin = StripLead0(trackInfo.group(minG)) + u":"
            else: trMin = u""
            if secG > 0: trSec = trackInfo.group(secG)
            else: trSec = u""

            trNum = StripSpaces(trNum)
            trDisc = StripSpaces(trDisc)
            trTitle = StripSpaces(trTitle)
            trMin = StripSpaces(trMin)
            trSec = StripSpaces(trSec)

            if isInt(trDisc) and len(trNum) > 0: #Non-vinyl disc:
                toWrite.append(trDisc + '.' + trNum + '|' + StripSpaces(trTitle) + '|' + trMin + trSec)
            else:
                toWrite.append(trDisc + trNum + '|' + StripSpaces(trTitle) + '|' + trMin + trSec)
            #Replace captures with empty string so they are not matched again
            oneline = re.sub(trackInfo.group(tnumG), u"", oneline, 1, re.M|re.U)
            oneline = re.sub(trackInfo.group(titleG), u"", oneline, 1, re.M|re.U)
            oneline = re.sub(trackInfo.group(minG), u"", oneline, 1, re.M|re.U)
            oneline = re.sub(trackInfo.group(secG), u"", oneline, 1, re.M|re.U)
            trackInfo = re.search(pattern, oneline, re.M|re.U)
    return toWrite

#----Classical linking function (should work for all source sites):----

def WriteClassical(tracks):
    '''
    takes a list of nearly finished tracks separated by | and inserts links to classical works where apt.
    tracks = list of RYM-format tracks
    '''
    tcopy = tracks[:]
    #create copy list of track info
    clines = []
    for line in tcopy:
        clines.append(line.split('|'))
    toInsert = []
    numlist = []
    #create list of track numbers, for placeholder finding
    for line in clines:
        if line[0]:
            numlist.append(line[0])
        else:
            if u"[/b]" not in line[1]:
                numlist.append(u"") #Create blank entries for sub-tracks (where works may be linked), but not main titles
        #Also, perform this capitalization if there is "##." where ## may be a roman numeral:
        moveSearch = re.search(ur"(.*)((\d+|((xc|x?l|l?x{1,3})(ix|iv|v?i{0,3})|(xc|xl|l?x{0,3})(ix|i?v|v?i{1,3}))\. )(.+))$", line[1], re.I|re.M|re.U)
        if moveSearch:
            oldlang = global_settings["lang"][:]
            global_settings["lang"] = global_settings["mvlang"]
            line[1] = moveSearch.group(1)+ moveSearch.group(3) + CapsFormat(moveSearch.group(9))
            global_settings["lang"] = oldlang

    wlines = global_settings["wlines"] #for convenience

    for x in range(len(wlines)): #first replace "disc-track" with "disc.track":
        wlines[x][0] = string.replace(wlines[x][0], u'-', u'.')

    for x in range(len(wlines)):
        if wlines[x][0] == u'p': #Time to fix placeholders
            if x == 0: #first line -> assume first numbered track from tracklist
                y = 0
                while len(numlist[y]) == 0:
                    y += 1
                    if y == len(numlist):
                        y = 0 #This shouldn't really happen?
                        break
                wlines[0][0] = numlist[y]
            else: #look for track in previous line:
                if wlines[x-1][0] != u'p': #Then it must be a track number:
                    try:
                        if len(wlines[x-1]) < 3: #Single track specified; easier case
                            wlines[x][0] = numlist[numlist.index(wlines[x-1][0]) + 1] #Assign to next elem in tracknum list
                        else: #Main work with movements. Need to use num movements:
                            wlines[x][0] = numlist[numlist.index(wlines[x-1][0]) + int(wlines[x-1][2])]
                    except:
                        print "Classical work error. Couldn't find tracknum for line:", wlines[x]
                else:
                    raise ValueError("Something went wrong. Can't assign track#s to works")

        if len(wlines[x]) > 2: #must be main work
            for w in range(len(clines)):
                if wlines[x][0] == clines[w][0]:
                    movements = None
                    if wlines[x][2][-1] != u'!':
                        if w == 0: #Need to create main work line above if we're on the first line
                            toInsert.append((0, [u'', wlines[x][1], u'']))
                        else:
                            if len(clines[w-1][0]) > 0: #Prev track is not a main work title, so make one:
                                toInsert.append((w, [u'', wlines[x][1], u'']))
                            elif clines[w-1][1][0:3] == '[b]' and clines[w-1][1][-4:] == '[/b]':
                                #[Work####,Title]. Remove bold for main works, as they are already bolded
                                clines[w-1][1] = wlines[x][1][:-1] + u',' + ReplaceBold(clines[w-1][1][3:-4]) + wlines[x][1][-1]
                            else: #Unbolded text without track number shouldn't happen, but maybe it might
                                clines[w-1][1] = wlines[x][1][:-1] + u',' + ReplaceBold(clines[w-1][1]) + wlines[x][1][-1]
                        #Now for movements:
                        if len(wlines[x]) <= 3: #Overwrite not specified
                            movements = GenerateMovements(wlines[x][1], wlines[x][2], None, "n")
                        else: #Overwrite specified:
                            movements = GenerateMovements(wlines[x][1], wlines[x][2], wlines[x][3:], "n")
                    else: #move num ends with !, so don't create a main title, just put in the work on the track and the movements:
                        wlines[x][2] = str(int(wlines[x][2][:-1]) + 1) #get rid of "!" and add 1 to include main work
                        if len(wlines[x]) <= 3: #Overwrite not specified
                            movements = GenerateMovements(OneWorkLess(wlines[x][1]), wlines[x][2], None, "n")
                        else: #Overwrite specified:
                            movements = GenerateMovements(wlines[x][1], wlines[x][2], wlines[x][3:], "y")
                    if type(movements) != types.NoneType:
                        for m in range(len(movements)):
                            clines[w+m][1] = movements[m][:-1] + u',' + ReplaceBold(clines[w+m][1]) + movements[m][-1]
        else: #must be remaining work
            for w in range(len(clines)):
                if wlines[x][0] == clines[w][0]:
                    if u"." in wlines[x][1]: #Split multi-work track:
                        wlines[x][1] = wlines[x][1].split(u".")
                    if type(wlines[x][1]) != types.ListType:
                        #If there's only one shortcut given:
                        clines[w][1] = wlines[x][1][:-1] + u',' + ReplaceBold(clines[w][1]) + wlines[x][1][-1]
                    else:
                        #Multiple shortcuts given. Try to find split locations:
                        clines[w][1] = ReplaceBold(clines[w][1])
                        splitInds = GenerateSplits(clines[w][1], len(wlines[x][1]))
                        if splitInds:
                            newMerged = u""
                            for e in range(0, len(splitInds[0])-1, 2):
                                nextWork = wlines[x][1][e/2][:-1] + ',' + clines[w][1][splitInds[0][e]:splitInds[0][e+1]] + wlines[x][1][e/2][-1]
                                newMerged += nextWork + splitInds[1] #Split with same char as before
                            clines[w][1] = newMerged[:len(newMerged) - len(splitInds[1])]
                        else: #Out of luck. Need to manually edit locations.
                            for link in wlines[x][1]:
                                if link == wlines[x][1][0]:
                                    clines[w][1] = link[:-1] + "," + clines[w][1] + link[-1]
                                else:
                                    clines[w][1] = clines[w][1] + link[:-1] + ", EDIT ME" + link[-1]

    #Now insert main work lines after loop, and in reverse:
    for q in range(len(toInsert)-1, -1, -1):
        clines.insert(toInsert[q][0], toInsert[q][1])

    #merge clines back to tracklist:
    for c in range(len(clines)):
        clines[c] = u"|".join(clines[c])

    tracks = clines
    return tracks


#----Extra functions----

def isInt(s):
    '''
    Checks to see if string s can exist as a valid integer. Used in "Other" sources.
    '''
    try:
        int(s)
        return True
    except ValueError:
        return False

def GenerateSplits(trackname, numsplits):
    '''
    Finds split indices for a track that contains multiple works. Accepts the following chars as split indicators: ; / & + , -
    '''
    splitchars = ['; ', ' / ', ' & ', ' + ', '/', ' - ', ', ']
    ind = 0
    while True:
        reg = ur'(.+)' #Generating new reg expression each time based on splitchars and number of splits:
        for c in range(numsplits-1):
            reg = reg + splitchars[ind] + ur'(.+)'
        findSplit = re.search(reg, trackname, re.M|re.U)
        if findSplit:
            splitInds = [0]
            for m in range(1,numsplits+1):
                if m == numsplits:
                    splitInds.append(splitInds[-1] + len(findSplit.group(m)))
                else:
                    splitInds.append(splitInds[-1] + len(findSplit.group(m)))
                    splitInds.append(splitInds[-1] + len(splitchars[ind]))
            return (splitInds, splitchars[ind])
        ind += 1
        if ind == len(splitchars):
            print "Couldn't find split locations. Cut and paste into appropriate location."
            return False

def ReplaceBold(line):
    '''
    For classical work linking, removes bolding from titles (main works are auto-bolded)
    '''
    line = string.replace(line, '[b]', '')
    line = string.replace(line, '[B]', '')
    line = string.replace(line, '[/b]', '')
    line = string.replace(line, '[/B]', '')
    return line

def AddDurations(origlen, extralen):
    '''
    Takes two unicode track lengths of the form #:## and returns unicode of added track lengths.
    '''
    origmin, origsec = string.split(origlen, u':', 1)
    extramin, extrasec = string.split(extralen, u':', 1)
    plusmins = 0
    addedsec = int(origsec) + int(extrasec)
    while addedsec > 60:
        plusmins += 1
        addedsec -= 60
    addedmin = int(origmin) + int(extramin) + plusmins
    newlen = str(str(addedmin) + u':' + str(addedsec)).decode("utf-8-sig")
    return newlen

def OneWorkLess(work):
    '''
    For use with classical linking. Simply returns the work that comes immediately before
    '''
    linkNum = re.search(r"(.+?)(\d+)(.+)", work, re.M|re.U)
    return linkNum.group(1) + str(int(linkNum.group(2)) - 1) + linkNum.group(3)


def GenerateMovements(mainlink, nummoves, overmoves, isExcl):
    '''
    Generates movement links based on either mainlink or overwrite input.
    '''
    movements = []
    moveNum = int(nummoves)
    if moveNum == 0:
        return None #Entering zero skips movement adding.

    if not overmoves: #If no overwrites specified
        linkNum = re.search(r'(.+?)(\d+)(.+)', mainlink, re.M|re.U)
        if linkNum:
            for i in range(1,moveNum+1):
                movements.append(linkNum.group(1) + str(int(linkNum.group(2)) + i) + linkNum.group(3))
        else:
            raise ValueError("Incorrect classical work format. Use [Work#####]")
    elif len(overmoves) == moveNum and isExcl == "n" or len(overmoves) == moveNum + 1 and isExcl == "y":
        movements = overmoves
    elif len(overmoves) == 1: #Automatic numbering of overwritten movements
        if isExcl == "n":
            linkNum = re.search(r'(.+?)(\d+)(.+)', overmoves[0], re.M|re.U)
            if linkNum:
                newMain = linkNum.group(1) + str(int(linkNum.group(2)) - 1) + linkNum.group(3)
                movements = GenerateMovements(newMain, nummoves, u'', "n") #Recursive call of new start link, and no overwrites
            else:
                raise ValueError("Incorrect classical work format. Use [Work#####]")
        elif isExcl == "y":
            linkNum = re.search(r'(.+?)(\d+)(.+)', mainlink, re.M|re.U)
            if linkNum:
                movements.append(linkNum.group(1)+ str(int(linkNum.group(2))) + linkNum.group(3))
                linkNum = re.search(r'(.+?)(\d+)(.+)', overmoves[0], re.M|re.U)
                if linkNum:
                    newMain = linkNum.group(1) + str(int(linkNum.group(2)) - 1) + linkNum.group(3)
                    movements.extend(GenerateMovements(newMain, int(nummoves) - 1, u'', "n")) #Recursive call of new start link, and no overwrites
                else:
                    raise ValueError("Incorrect classical work format. Use [Work#####]")
            else:
                raise ValueError("Incorrect classical work format. Use [Work#####]")
    else:
        raise ValueError("# of overwritten movements must either be = # of movements or = 1")
    return movements



def StripLead0(s):
    '''
    For track durations, trims any 0 at the beginning as long as there's at least 1 character
    '''
    while s[0] == '0' and len(s) > 1:
        if s[1] != ':':
            s = s[1:]
    return s

def StripSpaces(s):
    '''
    In the event that there are extra leading or trailing spaces, this simply replaces them in string s.
    '''
    s = re.sub(ur"^\s+", u"", s, 0, re.M|re.U)
    s = re.sub(ur"\s+$", u"", s, 0, re.M|re.U)
    return s

def FixLongTrack(hr, mn, sec):
    '''
    For turning ##:##:## durations into standard RYM ###:## durations
    '''
    fixedMin = int(hr) * 60 + int(mn)
    return str(fixedMin) + ":" + sec

def ToAlpha(num):
    '''
    For sub-tracks, takes an int and converts it to a letter of the alphabet. Works for any non-negative integer.
    '''
    alpha = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', \
             'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z']
    if num < 26:
        return alpha[num]
    else:
        return ToAlpha((num-26)/26) + ToAlpha(num%26)

def ToRoman(num):
    '''
    For classical sub-tracks, takes an int and converts it to a Roman numeral. Works for any non-negative integer up to about 5000
    '''
    roman = OrderedDict()
    roman[1000] = "M"
    roman[900] = "CM"
    roman[500] = "D"
    roman[400] = "CD"
    roman[100] = "C"
    roman[90] = "XC"
    roman[50] = "L"
    roman[40] = "XL"
    roman[10] = "X"
    roman[9] = "IX"
    roman[5] = "V"
    roman[4] = "IV"
    roman[1] = "I"

    def roman_num(num):
        for r in roman.keys():
            x, y = divmod(num, r)
            yield roman[r] * x
            num -= (r * x)
            if num > 0:
                roman_num(num)
            else:
                break

    return "".join([a for a in roman_num(num)])

#----Capitalization functions----

def spaced_lower_word(match):
    #For use in replacing matched uppercase words
    return u' ' + match.group(1).lower() + u' '

def upper_group2(match):
    #For use in capitalizing the first letter of each word
    return match.group(1) + match.group(2).upper()

def lower_group2(match):
    #For use in un-capitalizing the first letter of each word
    return match.group(1) + match.group(2).lower()

def FixKeySpacing(match):
    #returns trimmed key name "A-Flat Minor"
    return match.group(1) + u'-' + match.group(2)

def EngKeyCap(match):
    #returns corrected english key name: "... in A major/minor"
    return match.group(1) + match.group(2).upper() + match.group(3)

def MollCap(match):
    #returns proper german key name: "...a-Moll"
    return match.group(1)[0].lower() + match.group(1)[1:] + '-' + match.group(2)[0].upper() + match.group(2)[1:]

def DurCap(match):
    #returns proper german key name: "...Cis-Dur"
    return match.group(1)[0].upper() + match.group(1)[1:] + '-' + match.group(2)[0].upper() + match.group(2)[1:]

def OpusCap(match):
    #Capitalizes "Op. #" and "Opp. #"
    return match.group(1)[0].upper() + match.group(1)[1:] + '. ' + match.group(2)

def RomanNumCap(match):
    #Capitalizes Roman numerals in track names
    return match.group(1) + match.group(2).upper() + match.group(5)

def CapsFormat(s):
    '''
    Takes an entire track name s and capitalizes "correctly". Does not recognize proper nouns.
    '''
    engLowerWords = ['For', 'And', 'Of', 'In', 'But', 'On', \
                     'A', 'An', 'The', 'Yet', 'So', 'Nor', \
                     'Or', 'As', 'At', 'By', 'To', 'Vs.', 'Vs', \
                     'Etc', 'Etc.', "'N'", "O'"]

    if global_settings["lang"] == '0':
        return s #Avoid all title formatting operations

    #Preliminary classical spacing fixes:
    if global_settings["isClass"]:
        s = re.sub(ur"(N[ro])(?:\.|\.\s|\s|\-)(\d+)", ur"\1. \2", s, 0, re.I|re.U|re.M)
        s = re.sub(ur"(Op)(?:\.|\.\s|\s|\-)(\d+)", ur"\1. \2", s, 0, re.I|re.U|re.M)

    if global_settings["lang"] == 'e':
        #Capitalize each word in string:
        sList = s.split()
        for sword in range(len(sList)):
            oddCase = re.search(ur'(\w[A-Z]|\w\.\w)', sList[sword], re.M|re.U)
            if not oddCase:
                sList[sword] = re.sub(ur'(\W*)(\w)', upper_group2, sList[sword], 1, re.M|re.U)
        s = u" ".join(sList)
        #Only substitute words bound by spaces on both sides
        #...and with no major punctuation surrounding:
        for lword in engLowerWords:
            toReg = ur'(?<![\!\?\:\("\.\-\u2014\/\\])(?:\s)(' + re.escape(lword) + ur')(?:\s)(?![\!\?\:\)\"\.\-\u2014\/\\])'
            s = re.sub(toReg, spaced_lower_word, s, 0, re.M|re.U)
    elif settings["lang"] == 'f' or global_settings["lang"] == 's' or global_settings["lang"] == 'l' or global_settings["lang"] == 'i':
        #Romance languages: turn every word except the first (incl. after major punct) to lowercase.
        sList = s.split()
        for sword in range(1,len(sList)):
            oddCase = re.search(ur'(\w[A-Z]|\w\.\w)', sList[sword], re.M|re.U)
            if not oddCase:
                sList[sword] = re.sub(ur'(\W*)(\w)', lower_group2, sList[sword], 1, re.M|re.U)
                #Also, lowercase letters after apostrophes and hyphens:
                sList[sword-1] = re.sub(ur'(\w[\'\-])(\w)', lower_group2, sList[sword-1], 0, re.M|re.U)
            if sword == len(sList) - 1:
                oddCase = re.search(ur'(\w[A-Z]|\w\.\w)', sList[sword], re.M|re.U)
                if not oddCase:
                    sList[sword] = re.sub(ur'(\w[\'\-\u2019])(\w)', lower_group2, sList[sword], 0, re.M|re.U)
        s = u" ".join(sList)
        #Now capitalize new statements:
        s = re.sub(ur'(\!\s|\?\s|\:\s|\;\s|\"\s|\.\s|\-\s|\u2014\s|\/\s|\\\s|\(|\")(\w)', upper_group2, s, 0, re.M|re.U)
    else:
        pass #To be continued...

    #Fix any classical capitalization errors:
    if global_settings["isClass"]:
        #Trim spaces between, e.g., A - Flat Minor:
        s = re.sub(ur"\b([A-Za-z])\s+[\-\u2014]\s+(Flat|Sharp)", FixKeySpacing, s, 0, re.M|re.U)
        #Lowercase "major" or "minor"
        s = re.sub(ur"\b(\w\-?[b#]?[-\s])(Minor|Major)", lower_group2, s, 0, re.M|re.U)
        #Lowercase "flat" or "sharp":
        s = re.sub(ur"([A-Z]\s|[A-Z]\-)(Flat|Sharp)", lower_group2, s, 0, re.M|re.U)
        #Capitalize key name:
        s = re.sub(ur"\b(in )([a-z])($|[;,\:]|[b#]\b|[\-\s]flat|[\-\s]sharp|[\-\s]major|[\-\s]minor)", EngKeyCap, s, 0, re.M|re.U)
        #Uppercase "Moll" or "Dur"
        s = re.sub(ur"\b(\w{1,3})(?:\-|\s)(moll[$\W])", MollCap, s, 0, re.M|re.U|re.I)
        s = re.sub(ur"\b(\w{1,3})(?:\-|\s)(dur[$\W])", DurCap, s, 0, re.M|re.U|re.I)
        #Capitalize opus:
        s = re.sub(ur"\b(Opp?)(?:\.|\.\s|\s|\-)(\d+)", OpusCap, s, 0, re.I|re.U|re.M)
        #All caps roman numerals: (Saving only for classical because reasons)
        s = re.sub(ur"(^|\s+|\(|\[)((xc|xl|l?x{0,3})(ix|iv|v?i{0,3}))(\.|\s|\)|\]|$)", RomanNumCap, s, 0, re.I|re.U|re.M)

    return s

if __name__ == '__main__':
    tracklist = parse_tracklist_file(TracklistFilename)
    settings = parse_settings_file(SettingsFilename)
    toWrite = TrackListWrite(tracklist, settings)

    print "------------------------"
    print "Results written to txt:"
    print "------------------------"
    print ""
    for line in toWrite:
        print line

    out = open(OutFilename, 'w')
    #Actual text writing:
    for line in toWrite:
        out.write(line.encode('utf-8') + "\n")
    out.close()
