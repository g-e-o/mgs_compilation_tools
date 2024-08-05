import hashlib
import sys

from gcx import GcxData, DatFile

class DemoUnpacker:
    ''' Unpack/Repack PSX DEMO.DAT files using file names found in PC US version '''

    def __init__(self) -> None:

        self.demo_files = []

    def unpack(self, demo_dat):
        ''' Extract DEMO.DAT to demo files '''

        print( 'Unpacking demo: %s' % demo_dat )
        self.gcx = GcxData( demo_dat )
        self.demo_files = []
        count = 0
        offset = 0x800
        demo_offset = 0
        unknown_index = 0
        while offset <= len( self.gcx ):
            if offset == len( self.gcx ) or self.gcx.read_int( offset ) == 0x10080000:
                count += 1
                demo_file_data = self.gcx[demo_offset : offset]
                demo_file_hash = hashlib.sha256( demo_file_data ).hexdigest()
                if demo_file_hash in self.pc_demo_files.keys():
                    demo_name = self.pc_demo_files[demo_file_hash] + '.dmo'
                else:
                    print('Warning: could not resolve demo file name for', demo_file_hash)
                    demo_name = 'sUnknown%02d.dmo' % ( unknown_index )
                    unknown_index += 1
                self.demo_files.append( DatFile( demo_name, demo_offset, demo_file_data ) )
                demo_offset = offset
            offset += ( 0x800 - ( offset % 0x800 ) )

        print('Total demo files unpacked:', count)
        return self.demo_files

    def pack(self, demo_files):
        ''' Pack demo files into DEMO.DAT buffer '''

        print( 'Packing %d demo files' % len(demo_files) )
        self.gcx = GcxData()
        self.demo_files = demo_files
        count = 0
        for demo_file in demo_files:
            if demo_file.offset != len( self.gcx ):
                print( 'Error: bad offset for demo file', demo_file.name, hex(demo_file.offset), hex(len(self.gcx)) )
                sys.exit( 1 )
            self.gcx.extend( demo_file.data )
            count += 1

    # English demo files from PC version.
    pc_demo_files = {
        '4857b943aac4a06d4f235f9e4fb332cf6a0c8d868736a05c77ca52b11776ff1c': 's0101a0',
        '090f673858342f8e4de30fdbf459d2f89332c6877334f8f17b24631667345e0e': 's0101a1',
        '05c5db01623d1979f88d5a481a567c847b55573f8d608046bc133ea098a4f577': 's0101a2',
        '324eb55b3d671aa4ec817ded7824f618a050af5e06bdb3c90b5109f943d6104d': 's0102a0',
        '469721111cf436d6ae899d8428db8d694dc97dc62959dab4f0be6f13ad672e7e': 's0103a0',
        '0fa70e6386d4c3136dd3ba57ca359da36a249fc10a56a1240a0a0ab4f6ce461f': 's0104a0',
        '836e5efbc4d42ec5c3f03fc373a15a5a404778963cb04e6cd1891abf3661867d': 's0104c0',
        '055859b2c21234c37db005d6492c18447afaa03d7f6e160ab5e0f310ca5ad8db': 's0201a0',
        'a55552e050ca92b3eed7e4ee3c6c26e8cc9c8b70f819715b448463414b0366ca': 's0201a1',
        'f3f330e04bd06185e1e06ad0bd4a827338f5cf47809f179bb05ecd419a7e22de': 's0202a0',
        '72c16ce2f1d79e3d0ae05049b32b63c20313bc88997565501ed37ddd9b67575a': 's0202a1',
        '1081904e22eb2c89cfce879e94c1b90c91e452a41d6fe3a049a335dec174771b': 's0205a0',
        '7a4eb7d493c3a15c403b7da8a225a6de3ac7989190e9993adad1ab7bf9c6342f': 's0205a1',
        '9ea42d0fd3967df7b63915192979d3218febe44d4d27eab9b9d2a414ffb8d6f0': 's0205a2',
        'a54cdc92e5e9bcaa1ae5e8cc1203b446a51e8bac3905bcbfb01f71f3f937c9b8': 's0205a3',
        'fb7fcf0ade29ad31782c60b80ea44c12ddac14c359526b7d7e55f73dcb934765': 's0205a4',
        '7b3a0eac64def08aabfd99b3f9381fc0ab4e84d3ec26fdaac92048b8ae956111': 's0301a0',
        '1412465362258fd01ba2d26428636efac38c083589b6298318417be53c0351e1': 's0301a1',
        '6120bd88b71ef3762c369e180c60bcb263e0f009566704a6f20610adb8fbef1a': 's0302a0',
        'a3a65cb7753dea3888f3925be7561655a4920a86606ef143fc1f1640ad240564': 's0303a0',
        'c09e9133bb8f5cc275ea06883f9f25f6eb5a02fa15d467ddb63cfaecf777cf77': 's0304a0',
        'de06dab892aa0fad4ad65ad2ce77f9d08260400647d8ad608944332338a3da85': 's0501a0',
        'dc4ebb4541cba60ffc3dc7229ad66ace63810f8f35968014bf7c4a5bbf802e4f': 's0503a0',
        '539341002a477d4bff207731a0ea46718332f8e3febc040f5d98cd5cf2523e1d': 's0503a1',
        '7a134ef1aa247da8424551b2ef0557931478f45d516bae9c7e3e1bfe2f972cff': 's0504a0',
        'bf301695e2fe16c551213e00260b4ffe92c77808bb844d039510ab964e41e203': 's0504a2',
        'c69f2e76c4629f489ab3397ef9982e41dacf5bcbdb07fdb44f35434dc243b090': 's0504a4',
        'e71f7a8e4395d2fa0903d1251d9e12c19dc8f19b9e05e903b5892f2e534f39c5': 's0504a5',
        'cd7cd26d1390407e411b5cc13fda4464fd60e80b1272ae08be080e9a6130541e': 's0504a6',
        'd08a38685791c919d4a014959ee163a0a484ae986769db8538a83bb379816875': 's0701a0',
        '913ba633280d52e24368328c42d1c41bb31b827e926d8075a5d703e6eeca6de5': 's0702a0',
        '231f7b4a156a32018eb7bab7910e7d3a15d119fdd23e7d94cf45b2f5ec30f65b': 's0703a0',
        '75299083671a1ccfb46e01d5b1d08e6a3fffac5b0917fa6bf1bc9de78a60b929': 's0800a0',
        '633015b139a53eb0ad337a81765e4c4d364692e9d83cfc2a1c018e65921c106c': 's0801a0',
        '0ebb74c4c52997fe4f937d91b4205c49ad9226deacf2c54e31b863bb3aaa6d6d': 's0802a0',
        'a8053c702ea266b16d225b347290b3b0a75e1ca00e51e12bff29dce3e2d27a3c': 's0803a0',
        'cc07a1fa1f45cc032f0d83bd17412bb17a5cf69eeba147ad348c7c696b995d1d': 's0805a0',
        '68f1f0fc97d975a022464ee12b6db9a387f08d45ad546284d6cbdd3c0b0e3a0d': 's0901a0',
        'f72a1030a3d448d1e5a05fea5a3e56e5690b792bc59ac11dc78d507e3d766bdb': 's0901a1',
        '0271b1f95fd4cefa3b197e0ad5fdff273c556fa73836d0906aa863cd08afe570': 's0901a2',
        '63ea56afec8deb7e1267e210c733c9597355309ba0df24645c5405d90d0e4749': 's0901a3',
        '65f8222609347ac55a044019570c7dedbdb8e84dfba21dcd0f4bc32924541f9c': 's0901a5',
        '8b71469d32fa0bcf6eb7391c7fa50e0289e3d4ee65da44e1f8e69df788c2fded': 's0901a7',
        'fde0398c03c214d6c634bd3af7d733fc4bf79c4e238e77d153c2b38b2c47d3b5': 's0901a8',
        'ce30e2db6eccfce52abd8ce405b738879a58394aeef47d6ca362595316b74be9': 's0901a9',
        'c5c2f3c9746a27cb458d9df7c5c274e473007d59f21898643ad94c96ea456753': 's0901c0',
        '82162790d0612752c539d6c8ffc9a58faa50cc2f64ac372e30fb3fa076c3df1d': 's0901c1',
        '3c6e4bf8481d22bcc87e98489108c1f76ed67357b46a6c95a39df40ca465feb8': 's0901c2',
        '0f70652b903c2fef9036d210409f0ba6ccd6a1bfecaf0237f07ab1f428dc1050': 's0901c4',
        '74cbfc9f1119dfd370d3a46d295fdf59bcaf20e8597570e3620657f2028a893d': 's1001a0',
        '835eed52636f4cb0b6729b5b5ccefeca168b6954314ca048f675dcb06131c95e': 's1001a1',
        '449760da588104142625877332f83cdab350c28c819a6c7a658cf6fb0b8e2ca4': 's1001a2',
        '64ae36200578700f60fa01d611e492716496f4ddf0ce2f9e87a4e098ea69834a': 's1001a3',
        '353bf4776942f7323aff93cd7d0d91fb367d8667845a40e4b6946ba17299fe49': 's1003a0',
        'e473ef75272e50f1b4533712b84d7ee307cf04287ada61978e9e4de0511e95ba': 's1004a0',
        'fd4f3055ec24f9c8c7f262e4caca69bbbb0db5a074ef5a8a7a8483400ec07754': 's1101a0',
        '2a39b0a5d3dcac839f903bed88c80e8d88ffbdc348ba2c40a1423c14b59226f4': 's1103a0',
        'f743f962da16e61ea810fb951b4216b4d8482ab528e85947be4f9c520db25470': 's1105c0',
        'df059c0cbc191c9a14218a12513cfd96c9f0f400ed1427c5885824a23f456fba': 's1105c1',
        '8bab5d46f373227706cc5def9f76666cac683b9546c530ef1a68054276e0422a': 's1105c2',
        '891cbbc723276a4d9fb4ca625dfeb9766e5db0c22f4dc4b99d803e9b3ed80ae7': 's1106a0',
        '905fd8ff00b82992853b9e64ed8039ab2b723c94dc0842d3b59739944932bc20': 's1201a0',
        'adf997b9f70c42c6e4fa46c122beff8dc33c1b921a11eb13911c1f5dc4f35836': 's1202a0',
        'c70cb22f3dbb11c9251b10a30c3a905bd6200a3c5c6aea884e59bde9eeedf801': 's1203a0',
        'c0a7f18605cdfb841a67b9b3e14796b45510b6caf4aa2ae8a1f23ec8e516dc16': 's1207a0',
        '28ed9a1f35cd1d29fd2410d12fda3deef18bae8f942ebb2668962df087f5027b': 's1302a0',
        'ab89f6807cb1b771594be0a406d65b637cbd73c7540dd0b5f30b663200c0f690': 's1400a0',
        'f6a63b8498911c32647802029d274e9e588e3286a305a1bee3f56b367494d08f': 's1401a0',
        '1d781d4b31b13416490b4221c082fc645610395d1c87e8415c93a3e5701f05ab': 's1405b0',
        'a75ea86c86879531e7126e27bc08f4b5413e547004e63aa33cc01fe96eb66151': 's1502a0',
        'd88f55435f58d3a8274982ec949c270e6bbc0c315f58019993d4f915c72c727e': 's1600a0',
        '9f7429894e247cb1cb25936aa3ed890de247929ff8d2236d9f66c11d9cc5807d': 's1601a0',
        '046b00bc43b3e3b4f101f0fd4101e68fcbf853bede0a7e77ea2e7b0aaaa56d4e': 's1601a1',
        'a09b0244c6ec113bdca5e5b083fc9006884940a9360ce3b8557040b98aca9fda': 's1601a2',
        '6884cae4cafecd090a34d909ac567dd09b74f609d40e79af0094ebc1fc2533be': 's1701a0',
        '63bf22e97470e985c48289fd02d31053ac92746e8d853b786a3b39b614460865': 's1702a0',
        '794eb3a08208913b9569c023a4f2b8a7bd7802e99198d2d69f11210ba01a37e1': 's1704a0',
        '8af840d40e71084aef6fd5eb134b5bea877b9f86dad85d8d64cedcddd30fdc90': 's1803a0',
        'f52f4ab3c3fc96d4c47bc5a288949bc188f82cd8a7f6d8d581e673a21f9ec952': 's1803a1',
        '5fd4494331080a86d6f0496bf3ca59c6fa01ab0f0d13f48f75432fa96087885e': 's1901a0',
        '2c1f8689f7763400ef4dd04858676a653d6b47f560c6e2a8faf9cfd80ae47380': 's2000a0',
        'a094f77db645bf8b75f2c5606b16980202fb37bad7f2423bb421030e3ef2e403': 's2001a0',
        'fa48a31fcf7552f26d37ec07f05aeb98c5d69235fc34d4590b3ed7e7ca83ae4f': 's2001a1',
        'f0a0c375fde99841d8a9a722355d28c982e4e63cf50a09537aa084cbf940dd41': 's2003a0',
        'c8cac0b8a7443dd13b2848b6da2b61dfddba2b06dae0e3e8fdc1e17b22e383db': 's2003b0',
        '27dd161ed50aa53597b7419440862d94cbf0c90426621a1c516c06e2c2bf2639': 's2003c0',
        'a17d29a3962df893bd82f446b3dc40284dc194d9b84faeb72b43cc213c2119a7': 's2101a0',
        'af9e9c41775e3e839ad12a81f9fccfbcc7a155c588aca884c0a994b10ea1e58d': 's2105a0',
        '1b211e692fe7e5c12f17e353d697369edf6a5a3df6c523ebc1d16aec0d1778f0': 's2105c0',
        'f150681f69db3efb23ea8387079c70539c3f36bd27a237e2094e007c3c3c7f56': 's2201a0',
        'b9d6ef0251dad986ac6c28ddb19f7fd57e5516b48b490809e9323f77509ac79c': 's2202a0',
        'da35d2244d52d04b41bd0eb23c1a94dc6c86b0e9007de7036e9d98c91909ac4f': 's2301a0',
        '761b7d88481a89fcb5ece2f9568308e4b328b7d51c7dfc91659907d35a211d81': 's2302a0',
        '052390e45c8231c163f3025304c8d64314f503b726b0caab163664bec39e787e': 's2302a1',
        'fa3b5ddf7563c81f5f9133a3a2e5f9ca2ece38262604a9f3135eea83e738e303': 's2401a0',
        'e4cf5f9956c626ba0566ea86ea60f22a3620db420f04f6613c0d0e671e406089': 's2402a0',
        '5da9b648f0154dfc8c3bc9db2b73aab1c2ee0c931c28aae8bc7d85f8e110cc6c': 's2402a1',
        '6deb1ad03a3810bb400c622466f1ea7a5c9c41220b6a69db83b82a18f5852817': 's2404a0',
        '12ab88c499324c07d75369114935fd5656acd5623c6fe65eeb68497c4c9f80a0': 's2404a1',
        '7d4904cb5fa5900ec35f469cf007df37e41d598c899743e7f3c59b45d4290f64': 's2501b0',
        'e5362ea92646df79766317ac9119f688286f50869e23f4c618d3d1028e82d47a': 's2501b1',
        'd41d92bee87af585c0630c36239ced7265fdde49418ced075f423b4a66b682f3': 's2501b2',
        '652f411d9559f6047e530566faec5f0d9397e0d26db4c03e259ee5fbf8b31f02': 's2501c0',
        'e7ab17222c8b070f0daf5581956622b568656b96a75ee36d6b65f8b9ec9e99f7': 's2501e0',
        '6a68fab02505f903737f5746644d65e9eb7e1b13ab72dd300c443b567b13404f': 's2502a0',
        '13b383da4db08f42ce9c3175f0c3e770a663059cf0ff0a79bfcc4366e1789d1a': 's2602a0',
        'd47e01a76a9f2a3da7390ac851caf1b81fbc1348465f05393b75bc1159a12670': 's2603a0',
        'b51f13d62b615e60017cea6e88447a41cab7228182c033e319e7bf3671ecaa6a': 's2603c0',
        '3923a463da5056a6cf0b0bbbf9fcb16514b85bb01bfe23d92c69bdba1808f2d8': 's2801a0',
        '9364b3d77417226def49397b8393b357539762dfbf10de9da1989d62311fee00': 's2801a1',
        '0a17537babd0edd942e0408b1b5ea06c705b4a1fe7929c0e12039a36b1c5eddf': 's2801c0',
        '3fdc166a3976602c6adfe9ab4a0c212528ce81bbf8909fa16020ed9f15ae3145': 's2801c1',
        'c3a9a239d12d890fbbeac10cf112e21abb8f62edbac5e63f5591cecf4d1082fa': 's2801d0',
        '7acf942a061f37c91c5db8e44b2aa849e4156202b65e2e3719a59d204d2e78b5': 's2801d1',
        'bc06974d3195925e7b0acd72556b4a2d037fc9f09edef89bd0b507f5ed68bd55': 's2801e0',
        'aaaccc4d5dd8a65c87d83f40cf477a12bc174d86d13ae46a25bc607c71ce7b61': 's2801f0',
    }
