from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_iam as iam
from constructs import Construct


def create_web_ec2_instance(
    scope: Construct,
    app_name: str,
    stage: str,
    suffix: str,
    vpc: ec2.Vpc,
    security_group: ec2.SecurityGroup,
    instance_profile: iam.Role,
    key_pair_name: str,
) -> ec2.Instance:
    """Webサーバー用のEC2インスタンスを作成する

    Args:
        scope (Construct): 親のConstruct
        app_name (str): アプリケーション名
        stage (str): ステージ名
        suffix (str): インスタンス名のサフィックス
        vpc (ec2.Vpc): VPC
        security_group (ec2.SecurityGroup): EC2インスタンス用のセキュリティグループ
        instance_profile (iam.Role): インスタンスプロファイル
        key_pair_name (str): キーペア名
    Returns:
        ec2.SecurityGroup: EC2インスタンス
    """

    # キーペア名から既存のキーペアオブジェクトを取得
    key_pair = ec2.KeyPair.from_key_pair_name(
        scope, f"{app_name}_{stage}_key_pair_{suffix}", key_pair_name
    )

    user_data=ec2.UserData.for_linux()
    user_data.add_commands("dnf update -y")
    user_data.add_commands("dnf install -y wget")
    user_data.add_commands("cd")
    user_data.add_commands("wget https://aws-codedeploy-ap-northeast-1.s3.ap-northeast-1.amazonaws.com/latest/install")
    user_data.add_commands("chmod +x ./install")
    user_data.add_commands("sudo ./install auto")
    user_data.add_commands("dnf install -y httpd wget php-fpm php-mysqli php-json php php-devel")
    user_data.add_commands("systemctl enable codedeploy-agent")
    user_data.add_commands("systemctl start codedeploy-agent")
    
    user_data.add_commands("systemctl start httpd")
    user_data.add_commands("systemctl enable httpd")
    user_data.add_commands("echo 'Health check' > /var/www/html/health_check.html")

    return ec2.Instance(
        scope,
        id=f"{app_name}_{stage}_web_ec2_{suffix}",
        instance_name=f"{app_name}-{stage}-web-ec2-{suffix}",
        vpc=vpc,
        instance_type=ec2.InstanceType.of(
            ec2.InstanceClass.T3A, ec2.InstanceSize.MICRO
        ),
        machine_image=ec2.MachineImage.latest_amazon_linux2023(),
        key_pair=key_pair,
        block_devices=[
            ec2.BlockDevice(
                device_name="/dev/xvda", volume=ec2.BlockDeviceVolume.ebs(10)
            )
        ],
        role=instance_profile,
        security_group=security_group,
        # UserDataの使ってインスタンス起動時にスクリプトを実行、CodeDeployAgentとApacheをインストール
        user_data=user_data
    )
