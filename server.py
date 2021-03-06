import protocol, communication_channel, client, time, threading, random

class Server:

    '''
    A node in the OPE tree
    '''
    class OPE_Node:
        def __init__(self, v):
            self.value = v
            self.left = None
            self.right = None
            self.count = 1
            self.parent = None

    '''
    A dumb ML algo that learns something from a message and is able to 
    give recommendations to the server on how to encode a value
    '''
    class MachineLearner:

        def __init__(self):
            self.count = 0

        # updates state based on message
        def process_message(self, client_message):
            self.count += 1 

        # possibilities: NONE, INCREASING, DECREASING, RANDOM
        def get_recommendation(self):
            if (self.count == 0):
                return "NONE"
            else:
                return "INCREASING"

    def __init__(self, communication_channel):
        self.ope_table = {} 
        # use fake ope table for now -- instead of storing the OPE path, 
        # we store pointers to the node directly 
        self.fake_ope_table = {} 
        self.root = None
        self.learner = Server.MachineLearner()
        self.communication_channel = communication_channel

    def run(self):
        message = self.communication_channel.get()
        self.receive(message)

    def start(self):
        threading.Timer(1, self.run()).start()

    # HACK that allows us to use DCS with the fake OPE table. Actually 
    # just compares the "plaintext" portions of the ciphertext. Will
    # break with a real encryption scheme -- use real OPE tables!
    def DCS_hack(self, client_message):
        if client_message.ciphertext not in self.fake_ope_table.keys():
            #print "DCS HACKING"
            for key in self.fake_ope_table.keys():
                if key[:5] == client_message.ciphertext[:5]:
                    possible_nodes = self.fake_ope_table[key]
        else:
            # another hack to get non-dcs to work. basically, when we repeat keys,
            # we overwrite the ciphertext->node mapping in fake_ope_table. this 
            # causes problems and makes us get stuck in an infinite loop.
            possible_nodes = self.fake_ope_table[client_message.ciphertext]

        index = int(random.random()*len(possible_nodes))
        node = possible_nodes[index]
        return node or None

    '''
    Server response to a client message.
    '''
    def receive(self, client_message):
        #print "KEYS: " + str(self.fake_ope_table)
        self.learner.process_message(client_message)

        if (client_message.message_type.__repr__() == protocol.MessageType("move_left").__repr__()):
            current = self.DCS_hack(client_message)
            left_child = current.left
            if left_child:
                server_message = protocol.ServerMessage(ciphertext=left_child.value, client_message=client_message)
            else:
                server_message = protocol.ServerMessage(ciphertext=None, client_message=client_message)

        elif (client_message.message_type.__repr__() == protocol.MessageType("move_right").__repr__()):
            current = self.DCS_hack(client_message)
            right_child = current.right
            if right_child:
                server_message = protocol.ServerMessage(ciphertext=right_child.value, client_message=client_message)
            else:
                server_message = protocol.ServerMessage(ciphertext=None, client_message=client_message)

        elif (client_message.message_type.__repr__() == protocol.MessageType("get_root").__repr__()):
            if not self.root:
                server_message = protocol.ServerMessage(ciphertext=None, client_message=client_message)
            else:
                server_message = protocol.ServerMessage(ciphertext=self.root.value, client_message=client_message)

        elif (client_message.message_type.__repr__() == protocol.MessageType("insert").__repr__()):
            new_node = Server.OPE_Node(client_message.new_ciphertext)
            print "Server insert, new_ciphertext="+str(client_message.new_ciphertext)
            # root case
            if client_message.ciphertext == None:
                self.root = new_node
                if client_message.new_ciphertext in self.fake_ope_table.keys():
                    self.fake_ope_table[client_message.new_ciphertext] += [self.root]
                else:
                    self.fake_ope_table[client_message.new_ciphertext] = [self.root]
            else:
                node = self.DCS_hack(client_message)
                new_node.parent = node
                if (client_message.insert_direction == "left"):
                    node.left = new_node
                elif (client_message.insert_direction == "right"):
                    node.right = new_node
                if client_message.new_ciphertext in self.fake_ope_table.keys():
                    self.fake_ope_table[client_message.new_ciphertext] += [new_node]
                else:
                    self.fake_ope_table[client_message.new_ciphertext] = [new_node]
                # AVL rebalance
                while (node and node.parent):
                    rebalance(node.parent)
                    node = node.parent 
                self.update_root()
            server_message = protocol.ServerMessage(ciphertext=client_message.new_ciphertext, client_message=client_message)

        elif (client_message.message_type.__repr__() == protocol.MessageType("query").__repr__()):
            # trivial implementation since there is no data associated with a ciphertext besides itself
            server_message = protocol.ServerMessage(ciphertext=client_message.ciphertext, client_message=client_message)
        
        self.communication_channel.put(server_message)
        return server_message

    def update_root(self):
        while (self.root.parent != None):
            self.root = self.root.parent

    def pad(self, value):
        if (len(value) < ENC_LEN):
            value += "1"
        while (len(value) < ENC_LEN):
            value += "0"
        return value

    def unpad(self, value):
        r = value.rfind("1")
        return value[:r]

'''
These functions handle a rebalance of the tree upon insertion of a node. 
In our implementation, because we use a fake_ope_table with pointers to 
the nodes, this procedure doesn't take very long. However, in CryptDB, 
this procedure is the very time-consuming.

Specifically, we count two things: 1) the number of rebalance operations
and 2) the subtree size at each rebalanced node. This is because in CryptDB,
the time taken for each rebalance is proportional to the height of the subtree
rooted at that node.
'''

def subtree_size(node):
    if node is None:
        return 0
    if node.left is None and node.right is None:
        return 1
    elif node.left is None:
        return 1 + subtree_size(node.right)
    elif node.right is None:
        return 1 + subtree_size(node.left)
    else:
        return 1 + subtree_size(node.left) + subtree_size(node.right)

def counter(fn):
    def wrapper(*args, **kwargs):
        node = args[0]
        wrapper.subtree_sizes += [subtree_size(node)]
        return fn(*args, **kwargs)
    wrapper.subtree_sizes = []
    wrapper.__name__ = fn.__name__
    return wrapper

def height(node):
    if node is None:
        return 0
    if node.left is None and node.right is None:
        return 1
    elif node.left is None:
        return 1 + height(node.right)
    elif node.right is None:
        return 1 + height(node.left)
    else:
        return 1 + max(height(node.left), height(node.right))

def balance_factor(node):
    return height(node.left) - height(node.right)

def left_rotate(node):
    A = node #3
    B = node.right #4
    B.parent = A.parent #5 --- 3, 4
    A.parent = B #5 - 4 - 3
    A.right = B.left # 3 right - None
    B.left = A # 4 left - 3
    if B.parent:
        B.parent.left = B

def right_rotate(node):
    A = node # 5
    B = node.left # 4
    B.parent = A.parent # 4 is root
    A.parent = B # 4 - 5
    A.left = B.right # 5 has no children
    B.right = A 
    if B.parent:
        B.parent.right = B

'''
rebalance.subtree_sizes will return the subtree_sizes of every rebalance,
allowing us to figure out the speed of our insertion procedure (since each
rebalance needs to re-encode each of the nodes in the subtree).
len(rebalance.subtree_sizes) is the number of rebalances.
'''
@counter
def rebalance(node):
    #print "Rebalance count: " + str(rebalance.subtree_sizes)
    print "Rebalance time: " + str(sum(rebalance.subtree_sizes))
    if balance_factor(node) == -2:
        if balance_factor(node.right) == -1: # right-right case
            left_rotate(node)
        elif balance_factor(node.right) == 1: # right-left case
            right_rotate(node.right)
            left_rotate(node)
    elif balance_factor(node) == 2:
        if balance_factor(node.left) == 1: # left-left case
            right_rotate(node)
        elif balance_factor(node.left) == -1: # left-right case
            left_rotate(node.left)
            right_rotate(node)




