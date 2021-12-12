import numpy as np
import time
from PIL import Image
from tensorflow.keras.preprocessing import image as kp_image
import tensorflow as tf

from .vgg16model import num_style_layers, num_content_layers, get_model

image_path = '../test_image/'
content_file = image_path + 'girl.jpg'
style_file = image_path + 'style.jpg'
gpus = tf.config.experimental.list_physical_devices('GPU')
if gpus:
    tf.config.experimental.set_virtual_device_configuration(gpus[0],
                                                            [tf.config.experimental.VirtualDeviceConfiguration(
                                                                memory_limit=2048 + 512)])
tf.executing_eagerly()


def load_img(path_to_img, if_text):
    img = Image.open(path_to_img).convert("RGB")
    if if_text:
        img = img.resize((256, 256), Image.ANTIALIAS)
    else:
        img = img.resize((512, 512), Image.ANTIALIAS)
    img = kp_image.img_to_array(img)
    img = np.expand_dims(img, axis=0)
    return img


def load_and_process_img(path_to_img, if_text):
    img = load_img(path_to_img, if_text=if_text)
    img = tf.keras.applications.vgg19.preprocess_input(img)
    return img


def deprocess_img(processed_img):
    x = processed_img.copy()
    if len(x.shape) == 4:
        x = np.squeeze(x, 0)
    assert len(x.shape) == 3, ("Input to deprocess image must be an image of "
                               "dimension [1, height, width, channel] or [height, width, channel]")
    if len(x.shape) != 3:
        raise ValueError("Invalid input to deprocessing image")

    x[:, :, 0] += 103.939
    x[:, :, 1] += 116.779
    x[:, :, 2] += 123.68
    x = x[:, :, ::-1]

    x = np.clip(x, 0, 255).astype('uint8')
    return x


def get_content_loss(base_content, target):
    return tf.reduce_mean(tf.square(base_content - target))


def gram_matrix(input_tensor):
    channels = int(input_tensor.shape[-1])
    a = tf.reshape(input_tensor, [-1, channels])
    n = tf.shape(a)[0]
    gram = tf.matmul(a, a, transpose_a=True)
    return gram / tf.cast(n, tf.float32)


def get_style_loss(base_style, gram_target):
    gram_style = gram_matrix(base_style)

    return tf.reduce_mean(tf.square(gram_style - gram_target))  # / (4. * (channels ** 2) * (width * height) ** 2)


def get_feature_representations(model, content_path, style_path, if_text):
    content_image = load_and_process_img(content_path, if_text=if_text)
    style_image = load_and_process_img(style_path, if_text=if_text)
    stack_images = np.concatenate([style_image, content_image], axis=0)
    model_outputs = model(stack_images)
    style_features = [style_layer[0] for style_layer in model_outputs[:num_style_layers]]
    content_features = [content_layer[1] for content_layer in model_outputs[num_style_layers:]]
    return style_features, content_features


def compute_loss(model, loss_weights, init_image, gram_style_features, content_features):
    style_weight, content_weight = loss_weights
    model_outputs = model(init_image)
    style_output_features = model_outputs[:num_style_layers]
    content_output_features = model_outputs[num_style_layers:]
    style_score = 0
    content_score = 0
    weight_per_style_layer = 1.0 / float(num_style_layers)
    for target_style, comb_style in zip(gram_style_features, style_output_features):
        style_score += weight_per_style_layer * get_style_loss(comb_style[0], target_style)

    weight_per_content_layer = 1.0 / float(num_content_layers)
    for target_content, comb_content in zip(content_features, content_output_features):
        content_score += weight_per_content_layer * get_content_loss(comb_content[0], target_content)

    style_score *= style_weight
    content_score *= content_weight

    loss = style_score + content_score
    return loss, style_score, content_score


def compute_grads(cfg):
    with tf.GradientTape() as tape:
        all_loss = compute_loss(**cfg)
    total_loss = all_loss[0]
    return tape.gradient(total_loss, cfg['init_image']), all_loss


model = get_model()
model.compile(optimizer='rmsprop', loss='categorical_crossentropy', metrics=['accuracy'])
for layer in model.layers:
    layer.trainable = False


def style_transfer(content_path,
                   style_path,
                   num_iterations=20,
                   content_weight=1e3,
                   style_weight=1e-2, if_text=False):
    style_features, content_features = get_feature_representations(model, content_path, style_path, if_text=if_text)
    gram_style_features = [gram_matrix(style_feature) for style_feature in style_features]

    init_image = load_and_process_img(content_path, if_text=if_text)
    init_image = tf.Variable(init_image, dtype=tf.float32)

    opt = tf.optimizers.Adam(learning_rate=10.0)

    best_loss, best_img = float('inf'), None

    loss_weights = (style_weight, content_weight)
    cfg = {
        'model': model,
        'loss_weights': loss_weights,
        'init_image': init_image,
        'gram_style_features': gram_style_features,
        'content_features': content_features
    }

    start_time = time.time()
    global_start = time.time()

    norm_means = np.array(1)
    min_vals = -norm_means
    max_vals = 255 - norm_means
    for i in range(num_iterations):
        grads, all_loss = compute_grads(cfg)
        loss, style_score, content_score = all_loss
        opt.apply_gradients([(grads, init_image)])
        clipped = tf.clip_by_value(init_image, min_vals, max_vals)
        init_image.assign(clipped)

        if loss < best_loss:
            best_loss = loss
            best_img = init_image.numpy()

        print('Iteration: {}'.format(i))
        print('Total loss: {:.4e}, '
              'style loss: {:.4e}, '
              'content loss: {:.4e}, '
              'time: {:.4f}s'.format(loss, style_score, content_score, time.time() - start_time))
        start_time = time.time()

    print('Total time: {:.4f}s'.format(time.time() - global_start))
    best_img = Image.fromarray(deprocess_img(best_img))
    best_img = best_img.resize((1024, 1024), Image.ANTIALIAS)
    return best_img

# image = style_transfer(content_file, style_file)
# image.save('gen6.jpg')
