#!/usr/bin/env python
# -*- coding: ascii -*-

"""
Algorithm to mine disjunctive frequent itemsets

  This algorithm differs from the conjunctive itemset mining algorithms
  in the sense that it mines ORed itemsets instead of ANDed itemsets.

  The algorithm makes use of FPTree to store the dataset in a condensed form.

  Steps carried out by this algorithms are as follows:
  (Step 1)   Read the original dataset and create a new dataset with items
          mapped to a unique integer i.e. map each item to a unique integer ID.
          This step will be termed as preprocessing.

  (Step 2)   Scan the new dataset and calculate the frequency of each item present
          in the dataset.

  (Step 3)    We scan the dataset one more time to build an FPTree using the
          the frequencies of the items

  (Step 4)    We next traverse the itemset lattice in the top down order i.e.
          enumerating the lattice from items with higher cardinality to items
          with less cardinality.

  (Step 5)    For each such itemset, check if the itemset is a subset of any
          maximal infrequent itemset:
          - if NO: Use the FP Tree Property to find the support of the itemset.

  (Step 6)    If the itemset has support value greater than the min support
          threshold, then we add the itemset to the frequent itemset list,
          along with its support value.

  (Step 7)    Step 4 to 6 are repeated for all itemsets in the itemset lattice.
          The algorithm stops when all itemsets have been processed. The resultant
          list of frequent itemsets form the list of disjunctive frequent itemsets
          generated by our algorithm.

"""

import sys
from collections import defaultdict, namedtuple, OrderedDict
from copy import deepcopy
from operator import itemgetter, attrgetter
from queue import *

__author__ = 'Nihal Jain (nihal.jain@iitg.ernet.in)'
__version__ = '0.3'
__date__ = '20160810'

class FPNode(object):
    """Blueprint of a node in the FPTree"""

    def __init__(self, tree, item, nodeID, count=1):
        """Function to initialise all the attributes of a FPTree node"""
        self._tree = tree
        self._item = item
        self._count = count
        self._parent = None
        self._children = {}
        self._neighbour = None
        self._nodeID = nodeID

    @property
    def tree(self):
        """Returns the tree in which this node is present"""
        return self._tree

    @property
    def item(self):
        """Returns the item represented by this node"""
        return self._item

    @property
    def count(self):
        """Returns the frequency of the item represented by this node"""
        return self._count

    @property
    def parent(self):
        """Returns the parent node of this node"""
        return self._parent

    @property
    def children(self):
        """Returns the nodes which are children of this node"""
        return tuple(self._children.values())

    @property
    def neighbour(self):
        """"Returns the node which is the next entry in the header table corresponding to a certain item"""
        return self._neighbour

    @property
    def nodeID(self):
        """"Returns the id of this node in the fp tree"""
        return self._nodeID

    @parent.setter
    def parent(self, parentNode):
        """Function to set the parent node of this node"""
        if parentNode is not None and not isinstance(parentNode, FPNode):
            raise TypeError("The parent node of a node must be a FPNode")

        if parentNode and parentNode.tree is not self.tree:
            raise ValueError("The parent node of a node must belong to the same tree")
        self._parent = parentNode

    @neighbour.setter
    def neighbour(self, neighbourNode):
        """Function to set the neighbour node of this node"""
        if neighbourNode is not None and not isinstance(neighbourNode, FPNode):
            raise TypeError("The neighbour node of a node must be a FPNode")

        if neighbourNode and neighbourNode.tree is not self.tree:
            raise ValueError("The neighbour node of a node must belong to the same tree")
        self._neighbour = neighbourNode

    @property
    def root(self):
        """Return True if this node is the root node of the tree, otherwise False"""
        return self._item is None and self._count is None

    @property
    def leaf(self):
        """Return True if this node is a leaf node, otherwise False"""
        return len(self._children) == 0

    def incrementCount(self):
        """Function to increment the count of the item represented by this node"""
        if self._count is None:
            raise ValueError("No count value associated with the node")
        self._count += 1

    def searchChildren(self, item):
        """Check whether this node has a node representing item as a child.
        If yes, then return that node, otherwise return None"""
        try:
            return self._children[item]
        except KeyError:
            return None

    def addChild(self, childNode):
        """Function to add a node as child node of this node"""
        if childNode is not None and not isinstance(childNode, FPNode):
            raise TypeError("The child node of a node must be a FPNode")

        if not childNode.item in self._children:
            self._children[childNode.item] = childNode
            childNode.parent = self

    def __contains__(self, item):
        return item in self._children

    def inspect(self, depth=0):
        print(('  ' * depth) + repr(self))
        for child in self.children:
            child.inspect(depth + 1)

    def __repr__(self):
        if self.root:
            return "<%s (root)>" % type(self).__name__
        return "<%s %r (%r)>" % (type(self).__name__, self.item, self.count)


class FPTree(object):
    """
    The blueprint of an FP Tree.
    A FPTree will be used to store all the transactions in the database in condensed form. It may only store transaction
    items that are hashable(i.e. all items must be a valid dictionary key or a set member)
    """
    Header = namedtuple('Header', 'head tail')

    def __init__(self):
        """Function to initialise all the attributes of a FPTree node"""
        # this attribute stores the root node of the tree
        self._root = FPNode(self, None, 0, None)

        # this attribute stores a dictionary which maps items to all the nodes containing that item stored as a path
        # in the form of the head and tail of the path
        self._header = {}

        # a counter to keep track of number of nodes in this FPTree
        self._nodesCount = 0

    @property
    def root(self):
        """Returns the root node of the tree"""
        return self._root

    @property
    def nodesCount(self):
        """Returns the count of the total number of nodes in the tree"""
        return self._nodesCount

    def updateNodesCount(self):
        """Function to increment the count of the number of nodes by 1"""
        self._nodesCount += 1

    def addTransaction(self, transaction):
        """Function to add a transaction to the FP Tree"""
        # set the root of the tree as the current node
        currNode = self.root

        # for each item in the transaction
        for item in transaction:
            # search for a node representing the current item in the children list of the current node
            # if found return that node, else return None
            nextNode = currNode.searchChildren(item)

            # if a node representing the current item exists in the children list of current node, we increment the
            # count of that node by 1
            if nextNode:
                nextNode.incrementCount()

            # if no such node exists
            else:
                # update the counter for the number of nodes in the FP tree
                self.updateNodesCount()

                # create a new FPNode representing the current item
                nextNode = FPNode(self, item, self.nodesCount)

                # add this new node as a children of the current node
                currNode.addChild(nextNode)

                # update the header table and add a new entry for this new node in it
                self.updateHeader(nextNode)

            # set the current node to be next node, and processs the next item in the transaction
            currNode = nextNode

    def updateHeader(self, node):
        """Function to update the header table in order to add this node to the entry corresponding to the item
        represented by this node"""

        # the node should belong to the same tree as the tree represented by self
        assert self is node.tree

        # check if an entry exists for the item corresponding to the given node in the header table
        try:
            # if an entry exists, retrieve the header of this item
            headerOfItem = self._header[node.item]

            # set this node as the neighbour of the tail of the current path, represented by headerOfItem[1]
            # (haed, tail) = headerOfItem
            headerOfItem[1].neighbour = node

            # update the tail of this path in the entry corresponding to this item in the header table
            self._header[node.item] = self.Header(headerOfItem[0], node)

        # if there is no entry for this item in the header table
        # occurs when the item referenced in a transaction in the dataset for the first time
        except KeyError:
            # create a new header table entry corresponding to this item
            # this node will act as both the head and the tail of this newly created path
            self._header[node.item] = self.Header(node, node)

    def nodes(self, item):
        """Function to generate a list of nodes which contain the given item using the header table"""

        # try if an entry exists corresponding to the given item
        try:
            # set the current node to be the head of the path stored in the header entry of that item
            currNode = self._header[item][0]

        # return if no entry exists
        except KeyError:
            return

        # while tail is not reached
        while currNode:
            # generate the current node
            yield currNode

            # set the current node to be the next node of the path for that item
            currNode = currNode.neighbour

    def prefixPaths(self, item):
        """Function to generate the prefix paths in the FP Tree that end with the given item"""

        def collectPath(currNode):
            """Function to build the path corresponding to the given node"""

            # create an empty list which will be used to store the nodes in the path
            path = []

            # repeat while current node is not None and is not the root node of the FP Tree
            # build the path in bottom up manner, from the bottom node to the root node
            while currNode and not currNode.root:
                # append the current node to the path
                path.append(currNode)

                # set the new current node to be the parent node of the current node
                currNode = currNode.parent
            # reverse the path to get the original prefix path
            path.reverse()
            return path

        # for each node corresponding to the given item in the FP Tree, retrieve the prefix path for that node
        return (collectPath(node) for node in self.nodes(item))

    def items(self):
        """Function to generate one 2-tuple corresponding to each item represented in the FP Tree. The first element in
        the tuple is the item itself, while the second element is a generator which will yield all the nodes in the tree
        that correspond to that item"""
        for item in self._header.keys():
            yield (item, self.nodes(item))

    def inspect(self):
        """Function to print the complete FP tree"""
        print('FPTree')
        self.root.inspect(1)

        print('Routes')
        for item, nodes in self.items():
            print("     %r" % item)
            for node in nodes:
                print("     %r" % node)


def processDataset(filePath, numeric):
    """Function to process the given dataset and generate a list of lists containing transactions and their
    corresponding items"""

    # create a list to store the transactions present in the dataset
    transactions = []

    # try to open the file and read its contents
    try:
        # fp is a file object used to operate on the file
        # we open the file in raed mode
        fp = open(filePath, "r")

        # reads the file until EOF using readline() and returns a list containing the lines
        # and stores it in variable dataset
        dataset = fp.readlines()

        # close the file after reading is complete
        fp.close()

    # raise exception and exit if there is any read error or if file is not found
    except IOError:
        print("ERROR: file not found or unable to read data")
        sys.exit(-1)

    # process each line in the dataset
    for line in dataset:
        # check if items are numerals
        if numeric:

            # create a list to store the items present in a transaction
            transaction = []

            # convert each item into an integer and append it to the transaction
            for item in line.split():
                transaction.append(int(item))

            # append the transaction to the list of transactions
            transactions.append(transaction)

        # if items are not numerals
        else:
            #  after splitting the line into a list of items, append the items list to the transaction list
            transactions.append(line.split())

    #printTransactions(transactions)

    # return the list of lists containing the transactions
    return transactions


def printTransactions(transactions):
    """Function to print the transactions present in the list of lists containing the transactions"""
    for transaction in transactions:
        for item in transaction:
            print(str(item)+" ", end="", flush=True)
        print('.')


def filterTransactions(transactions, minSupp, includeSupp=False):
    """Function to filter out all items with support count less than minimum support. It returns a new list of
     transactions containing only the items satisfying the minimum support threshold. Each newly created transaction,
     within the list of transactions, stores items in a transaction ordered by frequency. Items with higher support
     value come first in the item list of the transaction."""

    # create a dictionary such that when a new key is encountered for the first time i.e. if it is already not there in
    # the mapping, a new entry is automatically created using the default_factory function which returns 0.
    itemsDict = defaultdict(lambda: 0)

    # count the frequency of each item and increment it by 1 whenever it is encountered in a transaction
    # a new key is created whenever an item is encountered for the first time, with its value set to 0
    for transaction in transactions:
        for item in transaction:
            itemsDict[item] += 1

    # debug
    #print(itemsDict)

    # create a new dictionary which contains only those items which have support count greater than or equal to minimum
    # support threshold

# commented for no filtering
#    itemsDict = dict((item , support) for item, support in itemsDict.items()
#                 if support >= minSupp)

    # debug
    #print("Item Dict:", itemsDict)

    # order the dictionary based on the support of the items, use lexicographical order to break ties
    itemsDictOrdered = OrderedDict(sorted(itemsDict.items(), key=itemgetter(1, 0), reverse=True))

    # debug
    #print("Ordered Item Dict:", itemsDictOrdered)

    itemsOrder = list(itemsDictOrdered.keys())

    # debug
    #print("Items Order", itemsOrder)

    def cleanTransactions(transaction):
        """Function to filter a transaction such that only those items remain which satisfy the minimum support
        threshold and sort the items in a transaction based on their frequency, with items having higher support coming
        first"""
        # filter transaction and sustain only items which have an entry in the itemDict
        transaction = list(filter(lambda v: v in itemsDictOrdered, transaction))

        # sort the transaction containing a list of items in items order
        transaction.sort(key=lambda v: itemsOrder.index(v))

        # return the new transaction
        return transaction

    # create a list to store the cleaned list of transactions
    transactionsNew =  []

    # map cleanTransactions function to each transaction present in the list of transactions
    # i.e. clean each transaction
    for transaction in map(cleanTransactions, transactions):
        transactionsNew.append(transaction)

    # debug
    #printTransactions(transactionsNew)

    # return the newly created cleaned list of transactions
    return transactionsNew, itemsOrder


def buildFPTree(transactions):
    """Function to build a fp tree from the given list of transactions"""

    # initialise tree to be fp tree object
    tree = FPTree()

    # insert each transaction in the transaction list to the fp tree
    for transaction in transactions:
        tree.addTransaction(transaction)

    # debug : print the resulting fp tree
    #tree.inspect()

    # return the object storing the resulting fp tree
    return tree

def checkPath(itemList, i, X_node, tree, itemsOrder):
    """Function to check whether the given prefix paths contains an item of the itemset. Returns True when item is a part
    of the given prefix path"""

    # set found to be false
    found = False

    # check if at index is valid and corresponds to an item in the itemset
    if i >= 0:

        # find the parent node of the gicen X_node
        Y_node = X_node.parent

        # repeat while
        while Y_node != tree.root:
            # check whether the item represented by current node is same as the item at index i in the given itemset
            if Y_node.item == itemList[i]:

                # if items are same, set found to be true
                found = True

                # break out of the current loop
                break
            # otherwise if the index of the item represented by Y_node in the items order is less than the order of the
            # i item in that list
            elif itemsOrder.index(Y_node.item) < itemsOrder.index(itemList[i]):
                # break
                break

            # set Y_node's parent to be the new Y_node
            Y_node = Y_node.parent

        # if item not found, move to the parent of the current Y_node
        if not found:
            found = checkPath(itemList, i - 1, X_node, tree, itemsOrder)
    else:
        # if not found, set found to false
        found = False

    # returns whether item found in the prefix path of the given node
    return found


def findSupportByPrefixPath(newList, tree, itemsOrder):
    """Function to find the support of given itemsets by using prefix path method"""

    # initialise the support value to be 0
    support = 0

    # loop over each element in the itemset
    for k in range(len(newList)):

        # set the x node to point to the head of x node in the header table
        X_node = tree._header[newList[k]][0]

        # while we donot reach the root node
        while X_node != None:

            # check whether the given path has the given item in it
            found = checkPath(newList, k - 1, X_node, tree, itemsOrder)

            # if not found add the count of X_node to the support count
            if not found:
                support += X_node.count

            # set the X_node's neighbour to be the new X_node
            X_node = X_node.neighbour

    # return the support value of the given itemset
    return support

def findSupportByBFS(newList, tree):
    """Function to calculate the support of the given itemset using the fp tree by traversing the fp tree in breadth
    first order"""
    # initialise the support to be  0
    support = 0

    # crteat an empty list which store true false depending on whether the node at index i has been visited by bfs
    # search
    visited = []

    # make number of node + 1 elements in the list and set them to be false by default
    for i in range(tree.nodesCount + 1):
        visited.append(False)

    # create an empty queue q
    q = Queue(maxsize=0)

    # set the first node i.e. the root node as visited
    visited[0] = True

    # push the root of the fp tree to the queue q
    q.put(tree.root)

    # repeat until the queue is not empty
    while not q.empty():
        # pop the queue and extract a node and make it the source node
        srcNode = q.get()
        #print("SRC:", srcNode.nodeID)

        # set the children nodes to be a list of nodes which are the children of the source node
        childrenNodes = srcNode.children

        # sort the list of children based on their support counts, in order of decreasing supports, breaking ties by
        # following lexicographical order
        sorted(childrenNodes , key=attrgetter('item'), reverse=True)
        sorted( childrenNodes , key=attrgetter('count'), reverse=True)

        # process each node in the list of children nodes
        for node in childrenNodes:

            # set flag to be false meaning that the item has not been found
            foundFlag = False

            # if the current child node is not visited before
            if not visited[node.nodeID]:
                # for each item in the list of items in the items
                for item in newList:
                    # check whether the node represented by the current node equals the current item in the itemset
                    if item == node.item:
                        # if so, add the count of that node to the support value
                        support += node.count

                        # set flag to be true meaning that the item is found
                        foundFlag = True

                        # break the loop if node represents this item
                        break

                # if item is found, continue to the next iteration of the for loop
                if foundFlag == True:
                    continue

                # set the current node to visited
                visited[node.nodeID] = True
                #print("Visited:", node.nodeID)

                # put this node into the queue
                q.put(node)

    # after processing all the nodes in bfs order, return the support
    return support

def generateItemsets(itemsList, start, end, depth, minSupp, fpt, itemsOrder, freqItemsets):
    """Function to find all the frequent itemset of the current itemset"""
    # set i to be the start index
    i = start

    # repeat while i lies between start and end (inclusive)
    while i >= end:
        # if we are depth end + 1, return
        if depth == end + 1:
            return

        #list of items in the current itemset
        newList = deepcopy(itemsList)

        # debug
        #print("Itemset before removal is: ", itemsList)

        # remove item i from the current itemset
        newList.remove(itemsList[i])

        # debug
        #print("Removed item i: ", i, "Current itemset is: ",i temsList[i])

        # find the support of current itemset
        val = findSupportByPrefixPath(newList, fpt, itemsOrder)
        #val = findSupportByBFS(newList, fpt)

        # if support of current itemset is greater than minimum support
        if (val >= minSupp):
            # debug
            #print("Added to frequent itemset list: ", newList, " With support: ", val)

            # append this frequent item into the list of frequent items
            freqItemsets.append({str(newList):val})

            # generate the next itemset by decrementing the value of i and depth by 1
            generateItemsets(deepcopy(newList), i - 1, end, depth - 1, minSupp, fpt, itemsOrder, freqItemsets)

        # decrement the value of i by 1
        i -= 1

def findFrequentItemsets(fpt, itemsOrder, minSupp):
    """"Function to find all the frequent itemsets in the fp tree, which is a consdensed representation of the given
    dataset"""
    # create an empty list to store the set of frequent itemsets
    freqItemsets = []

    # call generate itemsets function to find frequent itemsets
    generateItemsets(itemsOrder, len(itemsOrder) - 1, 0, len(itemsOrder), minSupp, fpt, itemsOrder, freqItemsets)

    print("Total " + str(len( freqItemsets)) + " frequent ORed Itemsets found.")

    # return the list of all frequent itemsets
    return freqItemsets

if __name__ == '__main__':
    import time
    from optparse import OptionParser
    # import the OptionParser module which will be used to parse the options passed as argument

    # start the timer
    startTime = time.clock()

    # initialise OptionParser object and pass a string which will be used to display usage
    opt = OptionParser(usage='%scriptName datasetPath')

    # add an option for minimum support initialisation
    opt.add_option('-s','--minimum-support', dest='minSupp', type='int', help='Minimum itemset support (default = 2)')

    # add an option to choose whether to use numbers to represent items
    opt.add_option('-n', '--numeric', dest='numeric', action='store_true', help='Convert the values in the dataset to '
                                                                                'numerals (default = false)')
    # set minimum support to 2, by default, if no option passed as  parameter
    opt.set_defaults(minSupp=2)

    # set numeric to false, by default, if no option passed as parameter
    opt.set_defaults(numeric=False)

    # parse the arguments passed to the program into options and args
    options, args = opt.parse_args()

    # check if number of args is at least 1,
    # if less display the error message
    if len(args) < 1:
        opt.error('ERROR: Must provide the path to a dataset file')


    print('-------------------------------------------------------------------')
    print('     Disjunctive Frequent Itemset Mining: DFS Based Algorithm')
    print('-------------------------------------------------------------------')
    print('Parameters are as follows....')
    print('Dataset File Path: ' + str(args[0]))
    print('Minimum Support Threshold: ' + str(options.minSupp))
    print('-------------------------------------------------------------------')

    # create a list to store the transactions present in the dataset
    transactions = []

    # process the dataset, and retrieve a list of lists containing a list of transactions and corresponding items
    transactions = processDataset(args[0], options.numeric)

    # create a list to store all the frequent itemsets
    result = []

    # process the list of transactions and generate a list of frequent itemsets
    transactions, itemsOrder = filterTransactions(transactions, options.minSupp)

    # build the fp tree for the passed list of transactions
    tree = buildFPTree(transactions)

    # find frequent itemsets for the given tree
    freqItemsets = findFrequentItemsets(tree, itemsOrder, options.minSupp)

    # debug
    #for itemset in freqItemsets:
    #    print(itemset)

    # end the timer and print the total execution time
    print(time.clock() - startTime, "seconds")
