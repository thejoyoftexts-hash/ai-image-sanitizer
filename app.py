import io
import numpy as np
import streamlit as st
from PIL import Image, ImageFilter, ImageOps
from scipy.ndimage import gaussian_filter, map_coordinates

# =====================================================================
# 1. ADVANCED IMAGE SANITIZATION FUNCTIONS
# =====================================================================


def create_edge_mask(img):
    """Detects text and sharp high-contrast boundaries to shield them

    from aggressive blurring filters.
    """
    gray_img = img.convert("L")
    edges = gray_img.filter(ImageFilter.FIND_EDGES)

    # Invert and threshold to create a stark binary mask for text/lines
    mask = ImageOps.invert(edges).convert("L")
    mask = mask.point(lambda x: 0 if x < 200 else 255)

    # Expand the mask slightly to ensure outer edges of typography are covered
    mask = mask.filter(ImageFilter.MaxFilter(3))
    return mask


def fourier_texture_scramble(img, magnitude_scramble=0.06):
    """Converts the image to the frequency domain using FFT, disrupts the

    periodic high-frequency textures AI detectors look for, and converts back.
    """
    img_array = np.array(img).astype(np.float32)
    scrambled_channels = []

    for c in range(3):  # Process Red, Green, and Blue channels independently
        channel = img_array[:, :, c]

        # Fast Fourier Transform to frequency space
        f_transform = np.fft.fft2(channel)
        f_shift = np.fft.fftshift(f_transform)

        magnitude = np.abs(f_shift)
        phase = np.angle(f_shift)

        # Target only the high frequencies (edges and fine textures)
        rows, cols = channel.shape
        crow, ccol = rows // 2, cols // 2
        mask = np.ones((rows, cols))
        # Protect the 30x30 low-frequency core center (shapes and base colors)
        mask[crow - 15 : crow + 15, ccol - 15 : ccol + 15] = 0

        # Inject white noise into the texture frequencies
        noise = (
            np.random.normal(0, magnitude_scramble, (rows, cols))
            * magnitude
            * mask
        )
        perturbed_magnitude = magnitude + noise

        # Recombine and execute Inverse FFT
        f_ishift = np.fft.ifftshift(perturbed_magnitude * np.exp(1j * phase))
        img_back = np.abs(np.fft.ifft2(f_ishift))

        scrambled_channels.append(img_back)

    scrambled_array = np.stack(scrambled_channels, axis=-1)
    return Image.fromarray(np.clip(scrambled_array, 0, 255).astype(np.uint8))


def apply_chromatic_aberration(img, shift_amount=1):
    """Simulates real camera glass anomalies by slightly shifting the

    Red and Blue color channels away from the Green baseline.
    """
    img_array = np.array(img)
    r, g, b = img_array[:, :, 0], img_array[:, :, 1], img_array[:, :, 2]

    r_shifted = np.roll(r, shift_amount, axis=0)
    r_shifted = np.roll(r_shifted, shift_amount, axis=1)

    b_shifted = np.roll(b, -shift_amount, axis=0)
    b_shifted = np.roll(b_shifted, -shift_amount, axis=1)

    return Image.fromarray(np.stack([r_shifted, g, b_shifted], axis=-1))


def advanced_scramble(img, warp_sigma=2.0, warp_alpha=0.7):
    """Applies a microscopic elastic distortion layer to bend and destroy

    the uniform mathematical pixel grids created by upscaling networks.
    """
    img_array = np.array(img)
    shape = img_array.shape

    dx = (
        gaussian_filter((np.random.rand(*shape[:2]) * 2 - 1), warp_sigma)
        * warp_alpha
    )
    dy = (
        gaussian_filter((np.random.rand(*shape[:2]) * 2 - 1), warp_sigma)
        * warp_alpha
    )

    x, y = np.meshgrid(np.arange(shape[1]), np.arange(shape[0]))

    scrambled_array = np.zeros_like(img_array)
    for i in range(shape[2]):
        channel_indices = (
            np.reshape(y + dy, (-1, 1)),
            np.reshape(x + dx, (-1, 1)),
            np.full((shape[0] * shape[1], 1), i),
        )
        scrambled_array[..., i] = map_coordinates(
            img_array, channel_indices, order=1
        ).reshape(shape[:2])

    return Image.fromarray(scrambled_array.astype(np.uint8))


def execution_pipeline(img_input, noise_level=0.02, quality=80):
    """The master pipeline combining text protection with deep texture destruction."""
    # Ensure safe conversion to pure RGB format
    if img_input.mode in ("RGBA", "LA") or (
        img_input.mode == "P" and "transparency" in img_input.info
    ):
        img_input = img_input.convert("RGBA")
        background = Image.new("RGBA", img_input.size, (255, 255, 255, 255))
        original_img = Image.alpha_composite(background, img_input).convert(
            "RGB"
        )
    else:
        original_img = img_input.convert("RGB")

    # Generate the layout preservation mask
    text_mask = create_edge_mask(original_img)

    # Phase 1: Attack background textures using Fourier and elastic warps
    processed_bg = original_img.copy()
    processed_bg = fourier_texture_scramble(
        processed_bg, magnitude_scramble=0.07
    )
    processed_bg = advanced_scramble(
        processed_bg, warp_sigma=2.5, warp_alpha=0.8
    )
    processed_bg = processed_bg.filter(ImageFilter.GaussianBlur(radius=0.5))

    # Downsample and rebuild background to degrade mathematical structures
    w, h = processed_bg.size
    processed_bg = processed_bg.resize(
        (int(w * 0.92), int(h * 0.92)), Image.Resampling.BILINEAR
    )
    processed_bg = processed_bg.resize((w, h), Image.Resampling.LANCZOS)

    # Phase 2: Overlay sharp original text elements back over the sanitized base
    composite_img = Image.composite(processed_bg, original_img, text_mask)

    # Phase 3: Global Unified Analog Distortions
    composite_img = apply_chromatic_aberration(composite_img, shift_amount=1)

    # Add global camera sensor noise
    img_array = np.array(composite_img).astype(np.float32)
    noise = np.random.normal(0, noise_level * 255, img_array.shape)
    noisy_array = np.clip(img_array + noise, 0, 255).astype(np.uint8)
    composite_img = Image.fromarray(noisy_array)

    # Final targeted context-sharpening pass using Unsharp Masking
    composite_img = composite_img.filter(
        ImageFilter.UnsharpMask(radius=1.0, percent=115, threshold=3)
    )

    return composite_img


# =====================================================================
# 2. STREAMLIT USER INTERFACE DEPLOYMENT
# =====================================================================

st.set_page_config(
    page_title="AI Image Sanitizer", page_icon="🛡️", layout="centered"
)

st.title("🛡️ Secure AI Image Sanitizer")
st.markdown(
    """
This app strips underlying software tracking layers, breaks invisible pixel-level watermarks (like SynthID), 
and scrambles frequency-domain AI signatures to dramatically lower fake-detection rankings while protecting typography.
"""
)

uploaded_file = st.file_uploader(
    "Drag and drop your AI-generated image here", type=["png", "jpg", "jpeg"]
)

if uploaded_file is not None:
    input_image = Image.open(uploaded_file)

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Original Image")
        st.image(input_image, use_container_width=True)

    # Configurations sidebar for custom tinkering
    st.sidebar.header("Sanitization Strengths")
    noise_slider = st.sidebar.slider("Sensor Noise (Grain)", 0.0, 0.05, 0.02, 0.005)
    quality_slider = st.sidebar.slider(
        "JPEG Compression Block Strength", 65, 95, 80, 5
    )

    if st.button("Run De-AI Sanitization Pipeline", use_container_width=True):
        with st.spinner("Breaking AI frequency artifacts and processing mask..."):
            # Execute processing core
            output_image = execution_pipeline(
                input_image, noise_level=noise_slider, quality=quality_slider
            )

            with col2:
                st.subheader("Sanitized Result")
                st.image(output_image, use_container_width=True)

            # Package output file data to browser download cache
            buf = io.BytesIO()
            output_image.save(buf, format="JPEG", quality=quality_slider)
            byte_im = buf.getvalue()

            st.success("Successfully processed image layout!")
            st.download_button(
                label="📥 Download Clean Image File",
                data=byte_im,
                file_name="sanitized_organic.jpg",
                mime="image/jpeg",
                use_container_width=True,
            )