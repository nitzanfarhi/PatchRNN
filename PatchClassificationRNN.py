'''
    PatchClassificationRNN
'''

import os
import numpy as np
from nltk.tokenize import TweetTokenizer
import clang.cindex
import clang.enumerations

# file path.
rootPath = './'
dataPath = rootPath + '/data/'
sDatPath = dataPath + '/security_patch/'
pDatPath = dataPath + '/positives/'
nDatPath = dataPath + '/negatives/'
tempPath = rootPath + '/temp/'

# hyperparameters.
_DiffEmbedDim_ = 128
_DiffMaxLen_ = 1000

# control
_DEBUG_ = 1

def main():
    # load data.
    if (not os.path.exists(tempPath + '/data.npy')) | (not _DEBUG_):
        dataLoaded = ReadData()
    else:
        dataLoaded = np.load(tempPath + '/data.npy', allow_pickle=True)
        print('[INFO] <ReadData> Load ' + str(len(dataLoaded)) + ' raw data from ' + tempPath + '/data.npy.')

    # get the diff file properties.
    if (not os.path.exists(tempPath + '/props.npy')) | (not _DEBUG_):
        diffProps = GetDiffProps(dataLoaded)
    else:
        diffProps = np.load(tempPath + '/props.npy', allow_pickle=True)
        print('[INFO] <GetDiffProps> Load ' + str(len(diffProps)) + ' diff property data from ' + tempPath + '/props.npy.')

    # get the diff token vocabulary.
    diffVocab, diffMaxLen = GetDiffVocab(diffProps)
    # get the max diff length.
    diffMaxLen = _DiffMaxLen_ if (diffMaxLen > _DiffMaxLen_) else diffMaxLen
    # get the diff token dictionary.
    diffDict = GetDiffDict(diffVocab)
    # get pre-trained weights for embedding layer.
    diffPreWeights = GetDiffEmbed(diffDict, _DiffEmbedDim_)
    # get the mapping for feature data and labels.
    diffData, diffLabels = GetDiffMapping(diffProps, diffMaxLen, diffDict)
    # change the tokentypes into one-hot vector.
    diffData = UpdateTokenTypes(diffData)

    print(diffData[0])

    # Splitdata train/test
    # Splitdata train/valid

    # TextRNNTrain
    # TextRNNTest

    return

def ReadData():
    '''
    Read data from the files.
    :return: data - a set of commit message, diff code, and labels.
    [[['', ...], [['', ...], ['', ...], ...], 0/1], ...]
    '''

    def ReadCommitMsg(filename):
        '''
        Read commit message from a file.
        :param filename: file name (string).
        :return: commitMsg - commit message.
        ['line', 'line', ...]
        '''
        fp = open(filename, encoding='utf-8', errors='ignore')  # get file point.
        lines = fp.readlines()  # read all lines.
        #numLines = len(lines)   # get the line number.
        #print(lines)

        # initialize commit message.
        commitMsg = []
        # get the wide range of commit message.
        for line in lines:
            if line.startswith('diff --git'):
                break
            else:
                commitMsg.append(line)
        #print(commitMsg)
        # process the head of commit message.
        while (1):
            headMsg = commitMsg[0]
            if (headMsg.startswith('From') or headMsg.startswith('Date:') or headMsg.startswith('Subject:')
                    or headMsg.startswith('commit') or headMsg.startswith('Author:')):
                commitMsg.pop(0)
            else:
                break
        #print(commitMsg)
        # process the tail of commit message.
        dashLines = [i for i in range(len(commitMsg))
                     if commitMsg[i].startswith('---')]  # finds all lines start with ---.
        if (len(dashLines)):
            lnum = dashLines[-1]  # last line number of ---
            marks = [1 if (' file changed, ' in commitMsg[i] or ' files changed, ' in commitMsg[i]) else 0
                     for i in range(lnum, len(commitMsg))]
            if (sum(marks)):
                for i in reversed(range(lnum, len(commitMsg))):
                    commitMsg.pop(i)
        #print(commitMsg)

        #msgShow = ''
        #for i in range(len(commitMsg)):
        #    msgShow += commitMsg[i]
        #print(msgShow)

        return commitMsg

    def ReadDiffLines(filename):
        '''
        Read diff code from a file.
        :param filename:  file name (string).
        :return: diffLines - diff code.
        [['line', ...], ['line', ...], ...]
        '''
        fp = open(filename, encoding='utf-8', errors='ignore')  # get file point.
        lines = fp.readlines()  # read all lines.
        numLines = len(lines)  # get the line number.
        # print(lines)

        atLines = [i for i in range(numLines) if lines[i].startswith('@@ ')]  # find all lines start with @@.
        atLines.append(numLines)
        # print(atLines)

        diffLines = []
        for nh in range(len(atLines) - 1):  # find all hunks.
            # print(atLines[nh], atLines[nh + 1])
            hunk = []
            for nl in range(atLines[nh] + 1, atLines[nh + 1]):
                # print(lines[nl], end='')
                if lines[nl].startswith('diff --git '):
                    break
                else:
                    hunk.append(lines[nl])
            diffLines.append(hunk)
            # print(hunk)
        # print(diffLines)
        # print(len(diffLines))

        # process the last hunk.
        lastHunk = diffLines[-1]
        numLastHunk = len(lastHunk)
        dashLines = [i for i in range(numLastHunk) if lastHunk[i].startswith('--')]
        if (len(dashLines)):
            lnum = dashLines[-1]
            for i in reversed(range(lnum, numLastHunk)):
                lastHunk.pop(i)
        # print(diffLines)
        # print(len(diffLines))

        return diffLines

    # create temp folder.
    if not os.path.exists(tempPath):
        os.mkdir(tempPath)
    fp = open(tempPath + 'filelist.txt', 'w')

    # initialize data.
    data = []
    # read security patch data.
    for root, ds, fs in os.walk(sDatPath):
        for file in fs:
            filename = os.path.join(root, file).replace('\\', '/')
            fp.write(filename + '\n')
            commitMsg = ReadCommitMsg(filename)
            diffLines = ReadDiffLines(filename)
            data.append([commitMsg, diffLines, 1])

    # read positive data.
    for root, ds, fs in os.walk(pDatPath):
        for file in fs:
            filename = os.path.join(root, file).replace('\\', '/')
            fp.write(filename + '\n')
            commitMsg = ReadCommitMsg(filename)
            diffLines = ReadDiffLines(filename)
            data.append([commitMsg, diffLines, 1])

    # read negative data.
    for root, ds, fs in os.walk(nDatPath):
        for file in fs:
            filename = os.path.join(root, file).replace('\\', '/')
            fp.write(filename + '\n')
            commitMsg = ReadCommitMsg(filename)
            diffLines = ReadDiffLines(filename)
            data.append([commitMsg, diffLines, 0])
    fp.close()

    #print(len(dataLoaded))
    #print(len(dataLoaded[0]))
    #print(dataLoaded)
    # [[['a', 'b', 'c', ], [['', '', '', ], ['', '', '', ], ], 0/1], ]
    # sample = dataLoaded[i]
    # commitMsg = dataLoaded[i][0]
    # diffLines = dataLoaded[i][1]
    # label = dataLoaded[i][2]
    # diffHunk = dataLoaded[i][1][j]

    # save dataLoaded.
    if not os.path.exists(tempPath + '/data.npy'):
        np.save(tempPath + '/data.npy', data, allow_pickle=True)
        print('[INFO] <ReadData> Save ' + str(len(data)) + ' raw data to ' + tempPath + '/data.npy.')

    return data

def GetDiffProps(data):
    '''
    Get the properties of the code in diff files.
    :param data: [[[line, , ], [[line, , ], [line, , ], ...], 0/1], ...]
    :return: props - [[[tokens], [nums], [nums], 0/1], ...]
    '''

    def RemoveSign(line):
        '''
        Remove the sign (+/-) in the first character.
        :param line: a code line.
        :return: process line.
        '''
        return ' ' + line[1:] if (line[0] == '+') or (line[0] == '-') else line

    def GetClangTokens(line):
        '''
        Get the tokens of a line with the Clang tool.
        :param line: a code line.
        :return: tokens - ['tk', 'tk', ...] ('tk': string)
                 tokenTypes - [tkt, tkt, ...] (tkt: 1, 2, 3, 4, 5)
                 diffTypes - [dft, dft, ...] (dft: -1, 0, 1)
        '''
        # remove non-ascii
        line = line.encode("ascii", "ignore").decode()

        # defination.
        tokenClass = [clang.cindex.TokenKind.KEYWORD,      # 1
                      clang.cindex.TokenKind.IDENTIFIER,   # 2
                      clang.cindex.TokenKind.LITERAL,      # 3
                      clang.cindex.TokenKind.PUNCTUATION,  # 4
                      clang.cindex.TokenKind.COMMENT]      # 5
        tokenDict = {cls: index + 1 for index, cls in enumerate(tokenClass)}
        #print(tokenDict)

        # initialize.
        tokens = []
        tokenTypes = []
        diffTypes = []

        # clang sparser.
        idx = clang.cindex.Index.create()
        tu = idx.parse('tmp.cpp', args=['-std=c++11'], unsaved_files=[('tmp.cpp', RemoveSign(line))], options=0)
        for t in tu.get_tokens(extent=tu.cursor.extent):
            #print(t.kind, t.spelling, t.location)
            tokens.append(t.spelling)
            tokenTypes.append(tokenDict[t.kind])
            diffTypes.append(1 if (line[0] == '+') else -1 if (line[0] == '-') else 0)
        #print(tokens)
        #print(tokenTypes)
        #print(diffTypes)

        return tokens, tokenTypes, diffTypes

    def GetWordTokens(line):
        '''
        Get the word tokens from a code line.
        :param line: a code line.
        :return: tokens - ['tk', 'tk', ...] ('tk': string)
        '''
        tknzr = TweetTokenizer()
        tokens = tknzr.tokenize(RemoveSign(line))
        return tokens

    def GetString(lines):
        '''
        Get the strings from the diff code
        :param lines: diff code.
        :return: lineStr - All the diff lines.
                 lineStrB - The before-version code lines.
                 lineStrA - The after-version code lines.
        '''
        lineStr = ''
        lineStrB = ''
        lineStrA = ''
        for hunk in lines:
            for line in hunk:
                # all lines.
                lineStr += RemoveSign(line)
                # all Before lines.
                lineStrB += RemoveSign(line) if line[0] != '+' else ''
                # all After lines.
                lineStrA += RemoveSign(line) if line[0] != '-' else ''

        return lineStr, lineStrB, lineStrA

    def GetDiffTokens(lines):
        '''
        Get the tokens for the diff lines.
        :param lines: the diff code.
        :return: tokens - tokens ['tk', 'tk', ...] ('tk': string)
                 tokenTypes - token types [tkt, tkt, ...] (tkt: 1, 2, 3, 4, 5)
                 diffTypes - diff types [dft, dft, ...] (dft: -1, 0, 1)
        '''
        # initialize.
        tokens = []
        tokenTypes = []
        diffTypes = []

        # for each line of lines.
        for hunk in lines:
            for line in hunk:
                #print(line, end='')
                tk, tkT, dfT = GetClangTokens(line)
                tokens.extend(tk)
                tokenTypes.extend(tkT)
                diffTypes.extend(dfT)
                #print('-----------------------------------------------------------------------')
        #print(tokens)
        #print(tokenTypes)
        #print(diffTypes)

        return tokens, tokenTypes, diffTypes

    #lines = data[0][1]
    #print(lines)
    #hunk = data[0][1][0]
    #print(hunk)
    #line = data[0][1][0][0]
    #print(line)

    # for each sample data[n].
    numData = len(data)
    props = []
    for n in range(numData):
        # get the lines of the diff file.
        diffLines = data[n][1]
        # properties.
        tk, tkT, dfT = GetDiffTokens(diffLines)
        label = data[n][2]
        prop = [tk, tkT, dfT, label]
        #print(prop)
        props.append(prop)
        print(n)

    # save dataLoaded.
    if not os.path.exists(tempPath):
        os.mkdir(tempPath)
    if not os.path.exists(tempPath + '/props.npy'):
        np.save(tempPath + '/props.npy', props, allow_pickle=True)
        print('[INFO] <GetDiffProps> Save ' + str(len(props)) + ' diff property data to ' + tempPath + '/props.npy.')

    return props

def GetDiffVocab(props):
    '''
    Get the vocabulary of diff tokens
    :param props - the features of diff code.
    [[[tokens], [nums], [nums], 0/1], ...]
    :return: vocab - the vocabulary of diff tokens. ['tk', 'tk', ...]
             maxLen - the max length of a diff code.
    '''

    # create temp folder.
    if not os.path.exists(tempPath):
        os.mkdir(tempPath)
    fp = open(tempPath + 'difflen.csv', 'w')

    # get the whole tokens and the max diff length.
    tokens = []
    maxLen = 0

    # for each sample.
    for item in props:
        tokens.extend(item[0])
        maxLen = len(item[0]) if (len(item[0]) > maxLen) else maxLen
        fp.write(str(len(item[0])) + '\n')
    fp.close()

    # remove duplicates and get vocabulary.
    vocab = {}.fromkeys(tokens)
    vocab = list(vocab.keys())

    # print.
    print('[INFO] <GetDiffVocab> There are ' + str(len(vocab)) + ' diff vocabulary tokens. (except \'<pad>\')')
    print('[INFO] <GetDiffVocab> The max diff length is ' + str(maxLen) + ' tokens. (hyperparameter: _DiffMaxLen_ = ' + str(_DiffMaxLen_) + ')')

    return vocab, maxLen

def GetDiffDict(vocab):
    '''
    Get the dictionary of diff vocabulary.
    :param vocab: the vocabulary of diff tokens. ['tk', 'tk', ...]
    :return: tokenDict - the dictionary of diff vocabulary.
    {'tk': 0, 'tk': 1, ..., '<pad>': N}
    '''

    # get token dict from vocabulary.
    tokenDict = {token: index for index, token in enumerate(vocab)}
    tokenDict['<pad>'] = len(tokenDict)

    # print.
    print('[INFO] <GetDiffDict> Create dictionary for ' + str(len(tokenDict)) + ' diff vocabulary tokens. (with \'<pad>\')')

    return tokenDict

def GetDiffEmbed(tokenDict, embedSize):
    '''
    Get the pre-trained weights for embedding layer from the dictionary of diff vocabulary.
    :param tokenDict: the dictionary of diff vocabulary.
    {'tk': 0, 'tk': 1, ..., '<pad>': N}
    :param embedSize: the dimension of the embedding vector.
    :return: preWeights - the pre-trained weights for embedding layer.
    [[n, ...], [n, ...], ...]
    '''

    # number of the vocabulary tokens.
    numTokens = len(tokenDict)
    # initialize the pre-trained weights for embedding layer.
    preWeights = np.zeros((numTokens, embedSize))
    for index in range(numTokens):
        preWeights[index] = np.random.normal(size=(embedSize,))
    print('[INFO] <GetDiffEmbed> Create pre-trained embedding weights with ' + str(len(preWeights)) + ' * ' + str(len(preWeights[0])) + ' matrix.')

    return preWeights

def GetDiffMapping(props, maxLen, tokenDict):
    '''
    Map the feature data into indexed data.
    :param props: the features of diff code.
    [[[tokens], [nums], [nums], 0/1], ...]
    :param maxLen: the max length of a diff code.
    :param tokenDict: the dictionary of diff vocabulary.
    {'tk': 0, 'tk': 1, ..., '<pad>': N}
    :return: np.array(data) - feature data.
             [[[n, {0~5}, {-1~1}], ...], ...]
             np.array(labels) - labels.
             [[0/1], ...]
    '''

    def PadList(dList, pad, length):
        '''
        Pad the list data to a fixed length.
        :param dList: the list data - [ , , ...]
        :param pad: the variable used to pad.
        :param length: the fixed length.
        :return: dList - padded list data. [ , , ...]
        '''

        if len(dList) <= length:
            dList.extend(pad for i in range(length - len(dList)))
        elif len(dList) > length:
            dList = dList[0:length]
        return dList

    # initialize the data and labels.
    data = []
    labels = []

    # for each sample.
    for item in props:
        # initialize sample.
        sample = []

        # process token.
        tokens = item[0]
        tokens = PadList(tokens, '<pad>', maxLen)
        tokens2index = []
        for tk in tokens:
            tokens2index.append(tokenDict[tk])
        sample.append(tokens2index)
        # process tokenTypes.
        tokenTypes = item[1]
        tokenTypes = PadList(tokenTypes, 0, maxLen)
        sample.append(tokenTypes)
        # process diffTypes.
        diffTypes = item[2]
        diffTypes = PadList(diffTypes, 0, maxLen)
        sample.append(diffTypes)

        # process sample.
        sample = np.array(sample).T
        data.append(sample)
        # process label.
        label = item[3]
        labels.append([label])

    if _DEBUG_:
        print('[DEBUG] data:')
        print(data[0:3])
        print('[DEBUG] labels:')
        print(labels[0:3])

    # print.
    print('[INFO] <GetDiffMapping> Create ' + str(len(data)) + ' feature data with ' + str(len(data[0])) + ' * ' + str(len(data[0][0])) + ' matrix.')
    print('[INFO] <GetDiffMapping> Create ' + str(len(labels)) + ' labels with 1 * 1 matrix.')

    # save files.
    if (not os.path.exists(tempPath + '/ndata_' + str(maxLen) + '.npy')) \
            | (not os.path.exists(tempPath + '/nlabels_' + str(maxLen) + '.npy')):
        np.save(tempPath + '/ndata_' + str(maxLen) + '.npy', data, allow_pickle=True)
        print('[INFO] <GetDiffMapping> Save the mapped numpy data to ' + tempPath + '/ndata_' + str(maxLen) + '.npy.')
        np.save(tempPath + '/nlabels_' + str(maxLen) + '.npy', labels, allow_pickle=True)
        print('[INFO] <GetDiffMapping> Save the mapped numpy labels to ' + tempPath + '/nlabels_' + str(maxLen) + '.npy.')

    return np.array(data), np.array(labels)

def UpdateTokenTypes(data):
    '''
    Update the token type in the feature data into one-hot vector.
    :param data: feature data. [[[n, {0~5}, {-1~1}], ...], ...]
    :return: np.array(newData). [[[n, 0/1, 0/1, 0/1, 0/1, 0/1, {-1~1}], ...], ...]
    '''

    newData = []
    # for each sample.
    for item in data:
        # get the transpose of props.
        itemT = item.T
        # initialize new sample.
        newItem = []
        newItem.append(itemT[0])
        newItem.extend(np.zeros((5, len(item)), dtype=int))
        newItem.append(itemT[2])
        # assign the new sample.
        for i in range(len(item)):
            tokenType = itemT[1][i]
            if (tokenType):
                newItem[tokenType][i] = 1
        # get the transpose of new sample.
        newItem = np.array(newItem).T
        # append new sample.
        newData.append(newItem)

    if _DEBUG_:
        print('[DEBUG] newData:')
        print(newData[0:3])

    # print.
    print('[INFO] <UpdateTokenTypes> Update ' + str(len(newData)) + ' feature data with ' + str(len(newData[0])) + ' * ' + str(len(newData[0][0])) + ' matrix.')

    return np.array(newData)


def SplitData():
    return

if __name__ == '__main__':
    main()