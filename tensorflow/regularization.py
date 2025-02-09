# These are all the modules we'll be using later. Make sure you can import them
# before proceeding further.
from __future__ import print_function
import numpy as np
import tensorflow as tf
# from six.moves import cPickle as pickle
import pickle


def accuracy(predictions, labels):
    return (100.0 * np.sum(np.argmax(predictions, 1) == np.argmax(labels, 1))
            / predictions.shape[0])


def reformat(dataset, labels):
    dataset = dataset.reshape((-1, image_size * image_size)).astype(np.float32)
    # Map 1 to [0.0, 1.0, 0.0 ...], 2 to [0.0, 0.0, 1.0 ...]
    labels = (np.arange(num_labels) == labels[:, None]).astype(np.float32)
    return dataset, labels


pickle_file = 'notMNIST.pickle'

with open(pickle_file, 'rb') as f:
    save = pickle.load(f)
    train_dataset = save['train_dataset']
    train_labels = save['train_labels']
    valid_dataset = save['valid_dataset']
    valid_labels = save['valid_labels']
    test_dataset = save['test_dataset']
    test_labels = save['test_labels']
    del save  # hint to help gc free up memory
    print('Training set', train_dataset.shape, train_labels.shape)
    print('Validation set', valid_dataset.shape, valid_labels.shape)
    print('Test set', test_dataset.shape, test_labels.shape)

# with tf.device('/cpu:0'):

# config = tf.ConfigProto()
# # config.gpu_options.allow_growth = True
# config.gpu_options.per_process_gpu_memory_fraction = 0.4

config = tf.ConfigProto(device_count = {'GPU': 0})

image_size = 28
num_labels = 10

train_dataset, train_labels = reformat(train_dataset, train_labels)
valid_dataset, valid_labels = reformat(valid_dataset, valid_labels)
test_dataset, test_labels = reformat(test_dataset, test_labels)
print('Training set', train_dataset.shape, train_labels.shape)
print('Validation set', valid_dataset.shape, valid_labels.shape)
print('Test set', test_dataset.shape, test_labels.shape)

nodes_count = 1024
batch_size = 128

# With gradient descent training, even this much data is prohibitive.
# Subset the training data for faster turnaround.
train_subset = 10000
train_subset = 1 * batch_size
# for beta_2 in [0, 0.005, 0.008, 0.009, 0.01]:

for beta_2 in [0.009]:

    graph_logistic_with_l2loss = tf.Graph()
    with graph_logistic_with_l2loss.as_default():
        # Input data.
        # Load the training, validation and test data into constants that are
        # attached to the graph.
        tf_train_dataset = tf.constant(train_dataset[:train_subset, :])
        tf_train_labels = tf.constant(train_labels[:train_subset])
        tf_valid_dataset = tf.constant(valid_dataset)
        tf_test_dataset = tf.constant(test_dataset)

        # Variables.
        # These are the parameters that we are going to be training. The weight
        # matrix will be initialized using random values following a (truncated)
        # normal distribution. The biases get initialized to zero.
        weights = tf.Variable(
            tf.truncated_normal([image_size * image_size, num_labels]))
        biases = tf.Variable(tf.zeros([num_labels]))

        # Training computation.
        # We multiply the inputs with the weight matrix, and add biases. We compute
        # the softmax and cross-entropy (it's one operation in TensorFlow, because
        # it's very common, and it can be optimized). We take the average of this
        # cross-entropy across all training examples: that's our loss.

        # we also need to add in a weighted l2 loss

        logits = tf.matmul(tf_train_dataset, weights) + biases
        loss_1 = tf.reduce_mean(tf.nn.softmax_cross_entropy_with_logits(logits, tf_train_labels))
        loss = tf.reduce_mean(loss_1 + beta_2 * tf.nn.l2_loss(weights) + beta_2 * tf.nn.l2_loss(biases))

        # Optimizer.
        # We are going to find the minimum of this loss using gradient descent.
        optimizer = tf.train.GradientDescentOptimizer(0.5).minimize(loss)

        # Predictions for the training, validation, and test data.
        # These are not part of training, but merely here so that we can report
        # accuracy figures as we train.
        train_prediction = tf.nn.softmax(logits)
        valid_prediction = tf.nn.softmax(
            tf.matmul(tf_valid_dataset, weights) + biases)
        test_prediction = tf.nn.softmax(tf.matmul(tf_test_dataset, weights) + biases)

    num_steps = 801

    with tf.Session(graph=graph_logistic_with_l2loss, config=config) as session:
        # This is a one-time operation which ensures the parameters get initialized as
        # we described in the graph: random weights for the matrix, zeros for the
        # biases.
        tf.global_variables_initializer().run()
        # print('Initialized')
        for step in range(num_steps):
            # Run the computations. We tell .run() that we want to run the optimizer,
            # and get the loss value and the training predictions returned as numpy
            # arrays.
            _, l, predictions = session.run([optimizer, loss, train_prediction])
            # if (step % 100 == 0):
            # print('Loss at step %d: %f' % (step, l))
            # print('Training accuracy: %.1f%%' % accuracy(predictions, train_labels[:train_subset, :]))
            # Calling .eval() on valid_prediction is basically like calling run(), but
            # just to get that one numpy array. Note that it recomputes all its graph
            # dependencies.
            # print('Validation accuracy: %.1f%%' % accuracy(valid_prediction.eval(), valid_labels))
        print('Beta/2 : %.3f Test accuracy: %.1f%%' % (beta_2, accuracy(test_prediction.eval(), test_labels)))

for beta in [0.003]:
    # for beta in [0.0, 0.001, 0.002, 0.003]:
    graph_relu = tf.Graph()
    with graph_relu.as_default():
        # Input data. For the training data, we use a placeholder that will be fed
        # at run time with a training minibatch.
        tf_train_dataset = tf.placeholder(tf.float32, shape=(batch_size, image_size * image_size))
        tf_train_labels = tf.placeholder(tf.float32, shape=(batch_size, num_labels))
        tf_valid_dataset = tf.constant(valid_dataset)
        tf_test_dataset = tf.constant(test_dataset)

        # Variables: weights and biases for the first classifier
        # this needs to be image_size * image_size x nodes_count to feed the data from the images into the RELU
        weights_1 = tf.Variable(tf.truncated_normal([image_size * image_size, nodes_count]))
        biases_1 = tf.Variable(tf.zeros([nodes_count]))

        # Training computation: the RELU
        relu = tf.nn.relu(tf.matmul(tf_train_dataset, weights_1) + biases_1)

        # Variables: weights and biases for the second classifier
        # this one needs to be nodes_count x num_labels to get the data back to the label set
        weights_2 = tf.Variable(tf.truncated_normal([nodes_count, num_labels]))
        biases_2 = tf.Variable(tf.zeros([num_labels]))

        # Training computation: the rest of the training computation from above
        logits = tf.matmul(relu, weights_2) + biases_2
        loss = tf.reduce_mean(tf.nn.softmax_cross_entropy_with_logits(logits, tf_train_labels)) + beta * tf.nn.l2_loss(
            weights_2) + beta * tf.nn.l2_loss(biases_2) + beta * tf.nn.l2_loss(weights_1) + beta * tf.nn.l2_loss(
            biases_1)
        # Optimizer.
        optimizer = tf.train.GradientDescentOptimizer(0.5).minimize(loss)

        # Predictions for the training, validation, and test data.
        train_prediction = tf.nn.softmax(logits)
        valid_prediction = tf.nn.softmax(
            tf.matmul(tf.nn.relu(tf.matmul(tf_valid_dataset, weights_1) + biases_1), weights_2) + biases_2)
        test_prediction = tf.nn.softmax(
            tf.matmul(tf.nn.relu(tf.matmul(tf_test_dataset, weights_1) + biases_1), weights_2) + biases_2)

    num_steps = 3001

    with tf.Session(graph=graph_relu, config=config) as session:
        tf.global_variables_initializer().run()
        # print("Initialized")
        for step in range(num_steps):
            # Pick an offset within the training data, which has been randomized.
            # Note: we could use better randomization across epochs.
            offset = (step * batch_size) % (train_labels.shape[0] - batch_size)
            # Generate a minibatch.
            batch_data = train_dataset[offset:(offset + batch_size), :]
            batch_labels = train_labels[offset:(offset + batch_size), :]
            # Prepare a dictionary telling the session where to feed the minibatch.
            # The key of the dictionary is the placeholder node of the graph to be fed,
            # and the value is the numpy array to feed to it.
            feed_dict = {tf_train_dataset: batch_data, tf_train_labels: batch_labels}
            _, l, predictions = session.run(
                [optimizer, loss, train_prediction], feed_dict=feed_dict)
            if (step % 500 == 0):
                # print("Minibatch loss at step %d: %f" % (step, l))
                # print("Minibatch accuracy: %.1f%%" % accuracy(predictions, batch_labels))
                # print("Validation accuracy: %.1f%%" % accuracy(
                #     valid_prediction.eval(), valid_labels))
                pass
        print("Beta/2: %.3f Test accuracy: %.1f%%" % (beta, accuracy(test_prediction.eval(), test_labels)))
