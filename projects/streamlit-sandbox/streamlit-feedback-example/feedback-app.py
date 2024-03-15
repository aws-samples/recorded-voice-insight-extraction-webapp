import time

import streamlit as st
import streamlit_feedback as stf

# Use this logger in your app for debugging and monitoring
# Output will surface in CloudWatch

logger = st.logger.get_logger(__name__)

# This pattern is important since this entire script is re-run every event
if "inputs_cached" not in st.session_state:
    st.session_state.inputs_cached = set()


def _submit_feedback(user_response, emoji=None, info_to_log={}):
    st.toast("Feedback submitted!", icon="🚀")
    # Log user response (e.g. the score) and info_to_log (e.g. what the user was rating)
    # This should end up searchable e.g. in CloudWatch
    log_dict = {**user_response, **info_to_log}
    logger.info(f"USER FEEDBACK SUBMITTED: {log_dict}")
    return


def main():
    """
    Main app function
    """

    input_col, output_col = st.columns([0.5, 0.5], gap="medium")

    with st.sidebar:
        input_selection, trigger_output_generation = display_sidebar()

    with input_col:
        display_inputs(input_selection)

    with output_col:
        display_outputs(input_selection, trigger_output_generation)


def display_sidebar():
    """
    Display sidebar where inputs can be selected
    """
    st.title("Feedback Demo")

    input_index = st.sidebar.selectbox(
        "Select input",
        range(5),
    )

    # This returns true the moment the button is clicked, then will return false after that
    button_pressed = st.button("Generate output", key="generate_output")

    input_selection = {"input_index": input_index}
    return input_selection, button_pressed


def display_inputs(input_selection):
    """
    Display selected inputs
    """
    st.header("Inputs")
    st.json(input_selection)


def display_outputs(input_selection, trigger_output_generation):
    """
    Generate outputs based on selected inputs, and display generated outputs
    """
    st.header("Outputs")

    # If you DIDN'T just click "Generate output"
    # and you've never computed this input before
    if (
        not trigger_output_generation
        and input_selection["input_index"] not in st.session_state.inputs_cached
    ):
        st.markdown("Use `Generate output` to generate outputs.")
        return

    # If you DID just click "Generate output",
    # or if you DIDN'T, but you already had before
    else:
        # generate output
        outputs = generate(input_selection)

        st.json(outputs)

        # Collect feedback on outputs
        stf.streamlit_feedback(
            feedback_type="thumbs",
            align="flex-start",
            on_submit=_submit_feedback,
            kwargs={
                "info_to_log": {
                    "log_input": input_selection,
                    "log_output": outputs,
                    "click_time": time.time(),
                }
            },
        )


@st.cache_data()
def generate(input_selection):
    """
    Generates outputs based on selected inputs
    """
    with st.spinner(text="Generating..."):
        time.sleep(2)
        st.success("Done")

    # Keep track of which inputs have been cached
    st.session_state["inputs_cached"].add(input_selection["input_index"])

    output = {"placeholder": "output"}
    logger.info(f"User clicked {input_selection}. Generated output: {output}")

    return output


if __name__ == "__main__":
    main()
