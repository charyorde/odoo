import graphene
#from common.odoorpc import RpcClient as Odoo


class UserInput(graphene.InputObjectType):
    id = graphene.String()
    email = graphene.String()


class User(graphene.ObjectType):
    id = graphene.String()
    email = graphene.String()


class GraphQLApi(graphene.ObjectType):
    user = graphene.Field(User, params=UserInput())
    hello = graphene.String(name=graphene.Argument(graphene.String, default_value="stranger"))

    def resolve_hello(self, args, context, info):
        return 'Hello ' + args['name']

    def resolve_user(self, args, context, info):
        # Either id or email is required to get a User
        if len(args) < 1:
            raise Exception("Either id or email is required to get a user")
        #user, code = Odoo('object').execute('res.users', 'find_user',
                                            #[args])
        #if code is 200:
            #return User(id=user.get('id'), email=user.get('email'))

Schema = graphene.Schema(query=GraphQLApi)
