import aws_cdk as core
import aws_cdk.assertions as assertions

from mas_stack.mas_stack_stack import MasStackStack

# example tests. To run these tests, uncomment this file along with the example
# resource in mas_stack/mas_stack_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = MasStackStack(app, "mas-stack")
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
