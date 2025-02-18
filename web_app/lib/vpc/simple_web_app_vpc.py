from aws_cdk import aws_ec2 as ec2
from constructs import Construct


class SimpleWebAppVPC(Construct):
    """一般的なWEBアプリケーションに使用するVPCを構築するモジュール"""

    _vpc: ec2.Vpc
    _elb_sg: ec2.SecurityGroup
    _web_sg: ec2.SecurityGroup
    _db_sg: ec2.SecurityGroup

    def __init__(self, scope: Construct, app_name: str, stage: str) -> None:
        """コンストラクタ

        Args:
            scope (Construct): 親のConstruct
            app_name (str): アプリケーション名
            stage (str): ステージ名
        """
        super().__init__(scope, f"{app_name}_{stage}_simple_vpc")

        # VPC
        # パブリックサブネット、NATゲートウェイに接続したプライベートサブネット、DB用のプライベートサブネットを作成
        # DB用のプライベートサブネットはNATゲートウェイには接続しない
        self._vpc = ec2.Vpc(
            self,
            id=f"{app_name}_{stage}_vpc",
            vpc_name=f"{app_name}-{stage}-vpc",
            max_azs=2,
            nat_gateways=1,
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    name=f"{app_name}-{stage}-public-subnet",
                    subnet_type=ec2.SubnetType.PUBLIC,
                ),
                ec2.SubnetConfiguration(
                    name=f"{app_name}-{stage}-protected-subnet",
                    subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS,
                ),
                ec2.SubnetConfiguration(
                    name=f"{app_name}-{stage}-private-subnet",
                    subnet_type=ec2.SubnetType.PRIVATE_ISOLATED,
                ),
            ],
        )

        # ALB、EC2、RDSそれぞれのセキュリティグループ
        self._elb_sg = ec2.SecurityGroup(
            self,
            id=f"{app_name}_{stage}_alb_sg",
            security_group_name=f"{app_name}-{stage}-alb-sg",
            vpc=self._vpc,
            allow_all_outbound=True,
        )
        self._elb_sg.add_ingress_rule(
            peer=ec2.Peer.any_ipv4(),
            connection=ec2.Port.tcp(80),
        )
        self._web_sg = ec2.SecurityGroup(
            self,
            id=f"{app_name}_{stage}_web_ec2_sg",
            security_group_name=f"{app_name}-{stage}-web-ec2-sg",
            vpc=self._vpc,
            allow_all_outbound=True,
        )
        self._web_sg.add_ingress_rule(
            peer=self._elb_sg,
            connection=ec2.Port.tcp(80),
        )
        self._db_sg = ec2.SecurityGroup(
            self,
            id=f"{app_name}_{stage}_rds_sg",
            security_group_name=f"{app_name}-{stage}-rds-sg",
            vpc=self._vpc,
            allow_all_outbound=True,
        )
        self._db_sg.add_ingress_rule(
            peer=self._web_sg,
            connection=ec2.Port.tcp(3306),
        )

    def get_vpc(self) -> ec2.Vpc:
        """VPCを取得する"""
        return self._vpc

    def get_public_subnets(self) -> list[ec2.ISubnet]:
        """パブリックサブネットを取得する"""
        return self._vpc.public_subnets

    def get_protected_subnets(self) -> list[ec2.ISubnet]:
        """インターネットに接続できるプライベートサブネットを取得する"""
        return self._vpc.private_subnets

    def get_private_subnets(self) -> list[ec2.ISubnet]:
        """プライベートサブネットを取得する"""
        return self._vpc.isolated_subnets

    def get_elb_sg(self) -> ec2.SecurityGroup:
        """ALBのセキュリティグループを取得する"""
        return self._elb_sg

    def get_web_sg(self) -> ec2.SecurityGroup:
        """EC2のセキュリティグループを取得する"""
        return self._web_sg

    def get_db_sg(self) -> ec2.SecurityGroup:
        """RDSのセキュリティグループを取得する"""
        return self._db_sg
