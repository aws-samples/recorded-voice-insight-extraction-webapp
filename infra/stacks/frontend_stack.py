from aws_cdk import Stack
from aws_cdk import aws_cognito as cognito

# import aws_cdk.aws_secretsmanager as secretsmanager
import boto3
from aws_cdk import Duration, RemovalPolicy  # SecretValue
from aws_cdk import aws_ec2 as ec2
from aws_cdk.aws_ecr_assets import DockerImageAsset
import os
from pathlib import Path
from aws_cdk import aws_ecs as ecs
from aws_cdk import aws_elasticloadbalancingv2 as elbv2
from aws_cdk import aws_iam as iam


class ReVIEWFrontendStack(Stack):
    def __init__(self, scope, id, **kwargs):
        super().__init__(scope, id, **kwargs)

        self.setup_cognito()
        self.docker_asset = self.build_docker_push_ecr()
        self.vpc = self.create_webapp_vpc()
        self.cluster, self.alb = self.create_ecs_and_alb(
            open_to_public_internet=True,
        )

    def setup_cognito(self):
        # Cognito User Pool
        user_pool_common_config = {
            "id": "review-app-cognito-user-pool-id",
            "user_pool_name": "review-app-cognito-user-pool",
            "auto_verify": cognito.AutoVerifiedAttrs(email=True),
            "removal_policy": RemovalPolicy.RETAIN,
            "password_policy": cognito.PasswordPolicy(
                min_length=8,
                require_digits=False,
                require_lowercase=False,
                require_uppercase=False,
                require_symbols=False,
            ),
            "account_recovery": cognito.AccountRecovery.EMAIL_ONLY,
            "advanced_security_mode": cognito.AdvancedSecurityMode.ENFORCED,
            "deletion_protection": True,
        }

        # Check if a user pool with this name already exists
        # Unfortunately there is no way to do this w/ constructs
        # (only search by ID, which I don't have a priori)
        cognito_client = boto3.client("cognito-idp", "us-east-1")
        existing_pools = cognito_client.list_user_pools(MaxResults=10)["UserPools"]
        found_existing_pool = False
        for pool in existing_pools:
            if pool["Name"] == "review-app-cognito-user-pool":
                self.cognito_user_pool = cognito.UserPool.from_user_pool_id(
                    self, "review-app-cognito-user-pool-id", user_pool_id=pool["Id"]
                )
                found_existing_pool = True
                break
        if not found_existing_pool:
            # Create a new user pool
            self.cognito_user_pool = cognito.UserPool(self, **user_pool_common_config)

        self.cognito_user_pool_id = self.cognito_user_pool.user_pool_id

        self.cognito_user_pool_client = self.cognito_user_pool.add_client(
            "review-app-cognito-client",
            user_pool_client_name="review-app-cognito-client",
            generate_secret=False,
            access_token_validity=Duration.minutes(30),
            auth_flows=cognito.AuthFlow(user_srp=True),
        )

        self.cognito_client_id = self.cognito_user_pool_client.user_pool_client_id

        # # Store created pool info as a secret, to be read by downstream streamlit application
        # # Todo: maybe replace this with systems manager? ssm?
        # secretsmanager.Secret(
        #     self,
        #     "review-app-cognito-secrets-id",
        #     secret_name="review-app-cognito-secrets",
        #     secret_object_value={
        #         "cognito-pool-id": SecretValue.unsafe_plain_text(
        #             self.cognito_user_pool_id
        #         ),
        #         "cognito-client-id": SecretValue.unsafe_plain_text(
        #             self.cognito_client_id
        #         ),
        #     },
        #     removal_policy=RemovalPolicy.DESTROY,
        # )

    def create_webapp_vpc(self):
        """Create self.vpc with self.ecs_security_group, self.alb_security_group"""
        # VPC for ALB and ECS cluster
        vpc = ec2.Vpc(
            self,
            "WebappVpc",
            ip_addresses=ec2.IpAddresses.cidr("10.0.0.0/16"),
            max_azs=2,
            vpc_name="ReVIEW-stl-vpc",
            nat_gateways=1,
        )

        ec2.FlowLog(
            self,
            "WebappVpcFlowLog",
            resource_type=ec2.FlowLogResourceType.from_vpc(vpc),
        )

        self.ecs_security_group = ec2.SecurityGroup(
            self,
            "SecurityGroupECS",
            vpc=vpc,
            allow_all_outbound=False,
            security_group_name="ReVIEW-stl-ecs-sg",
        )
        self.ecs_security_group.add_ingress_rule(
            peer=self.ecs_security_group,
            connection=ec2.Port.all_traffic(),
            description="Within Security Group",
        )
        self.ecs_security_group.add_egress_rule(
            peer=ec2.Peer.any_ipv4(),
            connection=ec2.Port.tcp(443),
            description="Required for boto3 call",
        )

        self.alb_security_group = ec2.SecurityGroup(
            self,
            "SecurityGroupALB",
            vpc=vpc,
            allow_all_outbound=False,
            security_group_name="ReVIEW-stl-alb-sg",
        )
        self.alb_security_group.add_ingress_rule(
            peer=self.alb_security_group,
            connection=ec2.Port.all_traffic(),
            description="Within Security Group",
        )
        self.alb_security_group.add_egress_rule(
            peer=self.ecs_security_group,
            connection=ec2.Port.tcp(8501),
            description="Communication with ECS SG",
        )

        # if self.ip_address_allowed:
        #     for ip in self.ip_address_allowed:
        #         if ip.startswith("pl-"):
        #             _peer = ec2.Peer.prefix_list(ip)
        #             # cf https://apll.tools.aws.dev/#/
        #         else:
        #             _peer = ec2.Peer.ipv4(ip)
        #             # cf https://dogfish.amazon.com/#/search?q=Unfabric&attr.scope=PublicIP
        #         self.alb_security_group.add_ingress_rule(
        #             peer=_peer,
        #             connection=ec2.Port.tcp(443),
        #         )

        # Change IP address to developer IP for testing
        # self.alb_security_group.add_ingress_rule(peer=ec2.Peer.ipv4("1.2.3.4/32"),
        # connection=ec2.Port.tcp(443), description = "Developer IP")

        self.ecs_security_group.add_ingress_rule(
            peer=self.alb_security_group,
            connection=ec2.Port.tcp(8501),
            description="ALB traffic",
        )

        return vpc

    def build_docker_push_ecr(self):
        # ECR: Docker build and push to ECR
        return DockerImageAsset(
            self,
            "StreamlitImg",
            # asset_name = f"{prefix}-streamlit-img",
            directory=os.path.join(Path(__file__).parent.parent, "frontend"),
        )

    def create_ecs_and_alb(self, open_to_public_internet=False):
        # ECS cluster and service definition

        cluster = ecs.Cluster(
            self,
            "Cluster",
            enable_fargate_capacity_providers=True,
            vpc=self.vpc,
            container_insights=True,
        )

        # alb_suffix = "" if open_to_public_internet else "-priv"

        # ALB to connect to ECS
        load_balancer_name = "ReVIEW-alb"
        alb = elbv2.ApplicationLoadBalancer(
            self,
            load_balancer_name,
            vpc=self.vpc,
            internet_facing=open_to_public_internet,
            load_balancer_name=load_balancer_name,
            security_group=self.alb_security_group,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC),
        )

        service_logs_prefix = f"load-balancers/{load_balancer_name}"
        # https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-properties-elasticloadbalancingv2-loadbalancer-loadbalancerattribute.html
        alb.log_access_logs(bucket=self.s3_logs_bucket, prefix=service_logs_prefix)

        self.resource_prefix = "ReVIEW-frontend-container"

        # log_group = CloudWatchLogGroup(
        #     scope=self,
        #     id="StreamlitContainerLogGroup",
        #     resource_prefix=self.resource_prefix,
        #     log_group_name="/ReVIEW/streamlit",
        # )

        task_execution_role = iam.Role(
            self,
            "WebContainerTaskExecutionRole",
            role_name=f"{self.resource_prefix}-role",
            assumed_by=iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
        )

        # log_group.grant_write(role=task_execution_role)
        self.grant_ecr_read_access(role=task_execution_role)

        # ecs_log_driver = ecs.LogDrivers.aws_logs(
        #     stream_prefix="AwsLogsLogDriver", log_group=log_group.log_group
        # )  # Full log stream name: [PREFIX]/[CONTAINER-NAME]/[ECS-TASK-ID]

        fargate_task_definition = ecs.FargateTaskDefinition(
            self,
            "WebappTaskDef",
            memory_limit_mib=512,
            cpu=256,
            execution_role=task_execution_role,
        )

        fargate_task_definition.add_container(
            "StreamlitAppContainer",
            # Use an image from DockerHub
            image=ecs.ContainerImage.from_docker_image_asset(self.docker_asset),
            port_mappings=[
                ecs.PortMapping(container_port=8501, protocol=ecs.Protocol.TCP)
            ],
            secrets={
                "COGNITO_CLIENT_ID": self.cognito_user_pool_client.user_pool_client_id,
                "COGNITO_POOL_ID": self.cognito_user_pool_id,
            },
            # "CLIENT_ID": ecs.Secret.from_ssm_parameter(self.ssm_client_id),
            # "API_URI": ecs.Secret.from_ssm_parameter(self.ssm_api_uri),
            # "WS_API_URI": ecs.Secret.from_ssm_parameter(self.ssm_ws_api_uri),
            # "BUCKET_NAME": ecs.Secret.from_ssm_parameter(
            #     self.ssm_s3_data_bucket_name
            # ),
            # },
            # logging=ecs_log_driver,
        )

        service = ecs.FargateService(
            self,
            "StreamlitECSService",
            cluster=cluster,
            task_definition=fargate_task_definition,
            service_name="ReVIEW-stl-front",
            health_check_grace_period=Duration.seconds(120),
            security_groups=[self.ecs_security_group],
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS
            ),
        )

        # ********* ALB Listener *********

        # alb.add_redirect()  # Redirect HTTP traffic to HTTPS

        http_listener = alb.add_listener(
            "ReVIEW-https-listener",
            # certificates=[elbv2.ListenerCertificate.from_arn(certificate_arn)],
            port=443,
            protocol=elbv2.ApplicationProtocol.HTTP,
            open=True,
        )

        http_listener.add_targets(
            "ReVIEW-https-tg",
            target_group_name="ReVIEW-https-tg",
            port=8501,
            protocol=elbv2.ApplicationProtocol.HTTP,
            targets=[service],
        )

        return cluster, alb
