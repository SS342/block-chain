import hashlib
import json
from textwrap import dedent
from time import time
from uuid import uuid4
from urllib.parse import urlparse
import requests
from flask import Flask, jsonify, request

class Blockchain(object):
    def __init__(self):
        self.chain = []
        self.current_transactions = []
        self.nodes = set()
        # create first block - блок генезиса 

        self.new_block(previous_hash=1, proof=100)

    def new_block(self, proof, previous_hash=None):
        # create a new block
        # proof - доказательство проведенной работы
        # previos hash - хеш предыдущего блока
        # return новый блок - dict

        block = {
            'index' : len(self.chain) + 1,
            'timestamp' : time(),
            'transactions' : self.current_transactions,
            'proof' : proof,
            'previous_hash' : previous_hash or self.hash(self.chain[-1])
        }

        # reload current_transactions
        self.current_transactions = []
        self.chain.append(block)

        return block

    def new_transaction(self, sender, recipient, amount):

        # sender - адресс отправителя
        # resipient - адресс получателя
        # amount -  сумма
        # return  индекс блока

        # add a new transaction in current transaction
        
        self.current_transactions.append({
            'sender'    : sender,
            'recipient' : recipient,
            'amount'    : amount
        })  

        return self.last_block['index'] + 1

    @staticmethod
    def valid_proof(last_proof, proof):
        """
        Подтверждение доказательства: Содержит ли hash(last_proof, proof) 4 заглавных нуля?
 
        :param last_proof: <int> Предыдущее доказательство
        :param proof: <int> Текущее доказательство
        :return: <bool> True, если правильно, False, если нет.
        """

        guess = f'{last_proof}{proof}'.encode()
        guess_hash = hashlib.sha256(guess).hexdigest()
        return guess_hash[:4] == "0000"

    def proof_of_work(proof, last_proof):
        # Найдите число «p«, которое хешировано с предыдущим созданным решением блока с хешем содержащим 4 заглавных нуля.
        """
        Простая проверка алгоритма:
         - Поиска числа p`, так как hash(pp`) содержит 4 заглавных нуля, где p - предыдущий
         - p является предыдущим доказательством, а p` - новым
 
        :param last_proof: <int>
        :return: <int>
        """

        proof = 0
        while Blockchain.valid_proof(last_proof, proof) is False:
            proof += 1

        return proof

    def register_node(self, address):
        """
        Вносим новый узел в список узлов
 
        :param address: <str> адрес узла , другими словами: 'http://192.168.0.5:5000'
        :return: None
        """
 
        parsed_url = urlparse(address)
        self.nodes.add(parsed_url.netloc)

    def valid_chain(self, chain):
        """
        Проверяем, является ли внесенный в блок хеш корректным
 
        :param chain: <list> blockchain
        :return: <bool> True если она действительна, False, если нет
        """
 
        last_block = chain[0]
        current_index = 1
 
        while current_index < len(chain):
            block = chain[current_index]
            print(f'{last_block}')
            print(f'{block}')
            print("\n-----------\n")
            # Проверьте правильность хеша блока
            if block['previous_hash'] != self.hash(last_block):
                return False
 
            # Проверяем, является ли подтверждение работы корректным
            if not self.valid_proof(last_block['proof'], block['proof']):
                return False
 
            last_block = block
            current_index += 1
 
        return True
 
    def resolve_conflicts(self):
        """
        Это наш алгоритм Консенсуса, он разрешает конфликты, 
        заменяя нашу цепь на самую длинную в цепи
 
        :return: <bool> True, если бы наша цепь была заменена, False, если нет.
        """
 
        neighbours = self.nodes
        new_chain = None
 
        # Ищем только цепи, длиннее нашей
        max_length = len(self.chain)
 
        # Захватываем и проверяем все цепи из всех узлов сети
        for node in neighbours:
            response = requests.get(f'http://{node}/chain')
 
            if response.status_code == 200:
                length = response.json()['length']
                chain = response.json()['chain']
 
                # Проверяем, является ли длина самой длинной, а цепь - валидной
                if length > max_length and self.valid_chain(chain):
                    max_length = length
                    new_chain = chain
 
        # Заменяем нашу цепь, если найдем другую валидную и более длинную
        if new_chain:
            self.chain = new_chain
            return True
 
        return False

    @property
    def last_block(self):
        # return last block
        return self.chain[-1]

    @staticmethod
    def hash(block):
        # хеширует блок
        # Создаем хеш SHA-256 блока
        # параметр на вход - блок - dict
        # return str
        block_string = json.dumps(block, sort_keys=True).encode() 
        return hashlib.sha256(block_string).hexdigest()


app = Flask(__name__)

# Генерируем уникальный на глобальном уровне адрес для этого узла
node_identifier = str(uuid4()).replace('-', '')

blockchain  = Blockchain()

@app.route('/mine', methods=['GET'])
def mine():
    # Мы запускаем алгоритм подтверждения работы, чтобы получить следующее подтверждение…
    last_block = blockchain.last_block
    last_proof = last_block['proof']
    proof = blockchain.proof_of_work(last_proof)
 
    # Мы должны получить вознаграждение за найденное подтверждение
    # Отправитель “0” означает, что узел заработал крипто-монету
    blockchain.new_transaction(
        sender="0",
        recipient=node_identifier,
        amount=1,
    )
 
    # Создаем новый блок, путем внесения его в цепь
    previous_hash = blockchain.hash(last_block)
    block = blockchain.new_block(proof, previous_hash)
 
    response = {
        'message': "New Block Forged",
        'index': block['index'],
        'transactions': block['transactions'],
        'proof': block['proof'],
        'previous_hash': block['previous_hash'],
    }
    return jsonify(response), 200


@app.route('/transactions/new', methods=['POST'])
def new_transaction():
    values = request.get_json()
 
    # Убедитесь в том, что необходимые поля находятся среди POST-данных 
    required = ['sender', 'recipient', 'amount']
    if not all(k in values for k in required):
        return 'Missing values', 400
 
    # Создание новой транзакции
    index = blockchain.new_transaction(values['sender'], values['recipient'], values['amount'])
 
    response = {'message': f'Transaction will be added to Block {index}'}
    return jsonify(response), 201


@app.route('/chain', methods=['GET'])
def full_chain():
    response = {
        'chain': blockchain.chain,
        'length': len(blockchain.chain),
    }
    return jsonify(response), 200


@app.route('/nodes/register', methods=['POST'])
def register_nodes():
    values = request.get_json()
 
    nodes = values.get('nodes')
    if nodes is None:
        return "Error: Please supply a valid list of nodes", 400
 
    for node in nodes:
        blockchain.register_node(node)
 
    response = {
        'message': 'New nodes have been added',
        'total_nodes': list(blockchain.nodes),
    }
    return jsonify(response), 201
 
 
@app.route('/nodes/resolve', methods=['GET'])
def consensus():
    replaced = blockchain.resolve_conflicts()
 
    if replaced:
        response = {
            'message': 'Our chain was replaced',
            'new_chain': blockchain.chain
        }
    else:
        response = {
            'message': 'Our chain is authoritative',
            'chain': blockchain.chain
        }
 
    return jsonify(response), 200


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
