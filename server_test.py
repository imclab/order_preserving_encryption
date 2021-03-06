import unittest, server, protocol, communication_channel

class TestServer(unittest.TestCase):

	def setUp(self):
		factory = communication_channel.CommunicationFactory()
		server_channel = factory.build_for("server")
		self.s = server.Server(server_channel)

	''' Inserts 5 into an empty tree at the server and asserts 
	the correctness of the server_message, subtree_size, 
	fake_ope_table, and root.value
	'''
	def test_insert_root(self):
		root_message = protocol.ClientMessage()
		root_message.insert(None, 5, 'left')
		server_message = self.s.receive(root_message)
		self.assertEqual(root_message.new_ciphertext, server_message.ciphertext)
		self.assertEqual(self.s.fake_ope_table,{root_message.new_ciphertext: self.s.root})
		self.assertEqual(server.Server.OPE_Node(root_message.new_ciphertext).value, self.s.root.value)

	''' Inserts 5 into an empty tree at the server, followed by 
	a get_root message. asserts the correctness of the 
	server_message and root.value
	'''
	def test_get_root(self):
		root_message = protocol.ClientMessage()
		root_message.insert(None, 5, 'left')
		server_message = self.s.receive(root_message)
		get_root_message = protocol.ClientMessage()
		get_root_message.get_root()
		server_message = self.s.receive(get_root_message)
		self.assertEqual(5, self.s.root.value)
		self.assertEqual(5, server_message.ciphertext)

	''' Inserts 5 into an empty tree at the server, followed by a 
	move_right message. asserts the correctness of the server_message
	'''
	def test_move_right(self):
		root_message = protocol.ClientMessage()
		root_message.insert(None, 5, 'left')
		server_message = self.s.receive(root_message)
		move_right_message = protocol.ClientMessage()
		move_right_message.move_right(5)
		server_message = self.s.receive(move_right_message)
		self.assertEqual(None, server_message.ciphertext)

	''' Inserts 5 and then 3 into an empty tree at the server, 
	followed by a move_left message and asserts the correctness
	of the server_message
	'''
	def test_move_left(self):
		root_message = protocol.ClientMessage()
		root_message.insert(None, 5, 'left')
		server_message = self.s.receive(root_message)
		insert_message = protocol.ClientMessage()
		insert_message.insert(5, 3, 'left')
		server_message_2 = self.s.receive(insert_message)
		move_left_message = protocol.ClientMessage()
		move_left_message.move_left(5)
		server_message_3 = self.s.receive(move_left_message)
		self.assertEqual(3, server_message_3.ciphertext)

	def test_rotate(self):
		# insert root
		root_message = protocol.ClientMessage()
		root_message.insert(None, 5, 'left')
		server_message = self.s.receive(root_message)
		# insert left child
		insert_message = protocol.ClientMessage()
		insert_message.insert(5, 3, 'left')
		server_message_2 = self.s.receive(insert_message)
		self.assertEqual(3, self.s.root.left.value)
		self.assertEqual(None, self.s.root.right)
		# insert a right child into unbalanced tree
		# insert_message_2 = protocol.ClientMessage()
		# insert_message_2.insert(3, 4, 'right')
		# server_message_3 = self.s.receive(insert_message_2)
		new_node = server.Server.OPE_Node(4)
		new_node.parent = self.s.root.left
		self.s.root.left.right = new_node

		self.assertEqual(3, server.height(self.s.root))
		self.assertEqual(2, server.subtree_size(self.s.root.left))
		self.assertEqual(2, server.balance_factor(self.s.root))

		server.left_rotate(self.s.root.left)
		self.assertEqual(4, self.s.root.left.value)
		self.assertEqual(3, self.s.root.left.left.value)
		self.assertEqual(3, server.subtree_size(self.s.root))

		server.right_rotate(self.s.root)
		server.Server.update_root(self.s)
		self.assertEqual(4, self.s.root.value)
		self.assertEqual(5, self.s.root.right.value)
		self.assertEqual(3, self.s.root.left.value)
		#self.assertEqual(3, server.subtree_size(self.s.root))

if __name__ == '__main__':
	unittest.main()