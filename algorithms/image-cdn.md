# Restricting time static images are allowed to be viewed

For version `v1.2.0`, I spent a *lot* of time finding new hug images and the artists who made them. Given my they are all publicily hosted (they have be if they are set as embed images on Discord) and my image naming was not particularly secretive (1.png, 2.png, 3.png etc) I wanted to prevent other people from using the API to just get the images because

1) I had spent a lot of time and effort on this and if used, I would like it be used though the bot directly and not copied by another bot
2) I went through quite a lot of lengths to find credit for artists and if re-used, people could just ignore the credit
3) I am planning on adding more content to the Greed Island system and I do not want people able to see new cards throuh the API like the already new (and secret) card 0.

> [!NOTE]
> Obviously all of this is kinda naive. Since I am publishing these images on GitHub, people can still just go and steal my work without credit to the artists. But I am not going to change my bot to closed source so this is a tradeoff I will have to live with.

Inspired by Discord, I wanted to now add a token to the request which would only be valid for 1) a certain amount of time and 2) certain whitlisted endpoint. So with token `abcdefg` you could only access `image/hugs/10.png` and only for 1 day. This would be enough to display it when the command was used but would prevent people from re-using that link and to request any images without a token.

## Initial implementation 
Initially, I implemented this by adding an extra endpoint called `/allow-endpoint` with an `Authorization` header set to the general admin key for the restricted API endpoints with a body something like this: 
```json
{
    "enpoint": "image/hugs/10.png"
}
```
This would then whitelist `api.killua.dev/image/hugs/10.png` if you requested it with the token returned by this endpoint in a `?token=` parameter. It did this by saving it to MongoDB with a set TTL (time to live) which MongoDB would automatically delete after a while. To catch two birds with one stone, the unique token returned by the endpoint was also the `ObjectId` MongoDB generated when inserting the object. This allowed me to avoid a headache of how to generate the token and made it easier to look up!

This was when I ran into my first problem: on startup, the bot needs to cache *all* card images so it is faster generating an image with them later. This would mean I'd need an `/allow-image` request for all 100+ cards! But this was an easy solve. I changed the endpoint body format to 
```json
{
    "endpoints": ["image/hugs/10.png", "image/hugs/11.png"]
}
```
along with some small logic changes, the returned token would now be valid for both of these images.

So this was the final result:
![image](https://github.com/user-attachments/assets/a71b2a1a-8e00-4e64-9fb8-679f79eb05b1)
![image](https://github.com/user-attachments/assets/a0400cb4-7653-4874-b0fc-42be555fc183)
![image](https://github.com/user-attachments/assets/0fea3a79-bc38-4c72-92e2-16ac2b10bf9c)
![image](https://github.com/user-attachments/assets/83fcd5c1-bc16-4156-90e3-c605f467d889)

## The rewrite
Plot twist! This was not the final result. I posted about this system to some programmer friends and [@luke](https://github.com/itslukej) suggested something else, entirely without the need for an `/allow-image` endpoint or a database...

Now this may have been obvious to you if you know much about this, I did not 😅. Instead of saving a token to the db, I could use a one way encryption system like `sha256` to just generate a token which could then be checked by the API. The token would consist of
```
token = sha256(endpoint + expiry + secret)
```

I can't lie, I was hesitant to implement this suggestion. My code worked, and "If it ain't broke, don't fix it". But thinking back to how obsessed I was [not to use a database for polls](compression.md) and how much more efficient this would be, after a few days and working on something else I decided to implement this version. However there were a few challenges.

### The challenges
#### How do I know if the token is still valid?
Now I know if you have worked on something like this before, this is probably trivial. However I did not look up how to create a system like this, instead throwing code at the problem hoping it would work. I mentioned earlier, `sha256` is a *one way* encryption/hashing algorithm. It will always hash the same input to the same output, but that output is not reversible. So how would I know if a token had expired if I couldn't get the `expiry` part of `sha256(endpoint + expiry + secret)` back? Or, even worse, how could I check the token is valid if I didn't know the `expiry` in the first place? I needed the exact same building blocks the hash was initially generated with, to generate it myself and check if they matched.


Well... after I ran back to luke, thinking I had spotted a fatal flaw in his logic and I could be lazy and not implement this system now, he gave me the most obvious answer: add `expiry` as another parameter in the request. That way I could check if it was in the past, and if not check if the token matched by generating a hash using the provided expiry. And the beauty of this was, if someone sneaky tried to add some extra time to the expiry parameter, the hashes would now not match anymore. So now cdn requests would be 
```
api.killua.dev/image/hugs/10.png?token=abcdef&expiry=1234
```
#### But what about a single token for multiple endpoints?
If you remember, earlier I mentioned needing to cache 100+ images at once. Given the much efficiency improved by using `sha256` over an API request, I *could* just generate a token for every image. It wouldn't be great, but it would work and still be decently fast. I thought if I could maybe repeat the logic I used before and instead use
```
token = sha256(endpoints + expiry + secret)
```
with multiple endpoints. However this would not work because I had no way of infering *all* `endpoints` from the request to a single one of those endpoints. But then as I was about to fall asleep one night I had a better idea: set defined groups. There were only few situations where I needed to bulk fetch a bunch of images, and for those cases I could define a single string that would whitelist a bunch of endpoints. Because it was one string, it would still work with `token = sha256(group + expiry + secret)` and it would solve my problem!

It turns out it was not that easy. From a normal request, I can infer what hash to check because I know what endpoint was requested. However I had no way of knowing that I should check for a `group` instead. So I played around a bit with the idea of a `?group` paremeter either set to `=true` or to a specific group like `=cards`. But I had already added one extra parameter to my image link (`expiry`) and I didn't really want to add another. Of course I could create a `HashMap` with every single endpoint pointing to a `Vec`tor of possibly groups that would allow it. But that would be a huge, terrible `HashMap`. I instead wanted some sort of pattern matching or lambda to see which endpoint whitelists which pattern. This brought me to this abomination: 
```rs
    static ref SPECIAL_ENDPOINT_MAPPING: HashMap<String, Box<dyn Fn(&str) -> Option<bool> + Sync + Send>> = 
    hashmap![
        "all_cards".to_string() => Box::new(
            |endpoint: &str| Some(endpoint.starts_with("cards/"))
        ) as Box<dyn Fn(&str) -> Option<bool> + Sync + Send>,
        "book".to_string() => Box::new(
            |endpoint: &str| Some(vec!["misc/book_default.png", "misc/book_first.png"].contains(&endpoint))
        ) as Box<dyn Fn(&str) -> Option<bool> + Sync + Send>
    ];
```
This was my attempt at shoving a lambda into a `HashMap` and took quite a while to do. But after a few seconds of post-code-clarity, I realized "But wait... I need to know the key to check if the endpoint is allowed for it... And I don't have the key/group...". Well, shit. I wanted what I had just made, but in reverse. I wanted all `values` where the `key` lambda matched the endpoint. Now the easy solve for that was doing a `for` loop, check if `value(endpoint).is_some()` and if so, compare the `token` to `sha256(key + expiry + secret)`. And this would work (I think Idk spoiler I did not end up doing that so I didn't test it), but it didn't really sit right with me. At that point I could have just itered through a list or a `HashMap<String, Vec<String>`, so what was the point of making it lambdas? And for some reason I was put off by the `O(n)` time complexity which wasn't even that bad, especially with the few keys I had and it being written in Rust. 

After searching online for a while, looking for a solution that was not just itering over things in `O(n)` time, I stumbled across `regex::RegexSet`. `RegexSet` takes in a `Vec`tor of regexes and then returns which, if any, match with the same time complexity as if it was a single regex expression. Perfect! 
This led me to my current (for real this time) implementation:

```rs
lazy_static::lazy_static! {
    pub static ref HASH_SECRET: String = std::env::var("HASH_SECRET").unwrap();
    static ref REGEX_SET: RegexSet = RegexSet::new([ // Regexes that the endpoint will be matched against
        r"cards/.*",
        r"misc/(book_default.png|book_first.png)",
        r"(boxes/.*|powerups/logo.png)"
    ]).unwrap();
    static ref SPECIAL_ENDPOINT_MAPPING: HashMap<usize, String> =
    [
        (0, "all_cards".to_string()), // If the first regex matches, `0` will be returned, so here I map the index to the strings
        (1, "book".to_string()),
        (2, "vote_rewards".to_string())
    ].iter().cloned().collect();
}

/// Perform the sha256(endpoint + expiry + secret) hash
pub fn sha256(endpoint: &str, expiry: &str, secret: &str) -> String {
    let mut hasher = Sha256::new();
    hasher.update(format!("{}{}{}", endpoint, expiry, secret));
    format!("{:x}", hasher.finalize())
}

/// Check if the token is valid and has not expired as well as if the
/// endpoint is allowed and the time has not expired
fn allows_endpoint(token: &str, endpoint: &str, expiry: &str) -> bool {
    // If the expiry is in the past, the token is invalid
    if expiry.parse::<u64>().unwrap()
        < SystemTime::now()
            .duration_since(SystemTime::UNIX_EPOCH)
            .unwrap()
            .as_secs()
    {
        return false;
    }
    sha256(endpoint, expiry, &HASH_SECRET) == token // If the endpoint and the token match, no group has to be tried
        || REGEX_SET.matches(endpoint).iter().any(|x| { // For each regex match, hash the group name and see if tokens match
            sha256(
                SPECIAL_ENDPOINT_MAPPING.get(&x).unwrap(),
                expiry,
                &HASH_SECRET,
            ) == token
        })
}
```
And this works like a charm! It is also pretty efficient.

## The final result

So now I can generate a hash pretty easily using this small python script:
```py
from hashlib import sha256
from datetime import datetime, timedelta

secret = "secret"
endpoint = "all_cards"
expiry = str(int((datetime.now() + timedelta(hours=1)).timestamp()))


sha256(f"{endpoint}{expiry}{secret}".encode()).hexdigest(), expiry
```

to get an output: 

<img width="540" alt="image" src="https://github.com/user-attachments/assets/6c6f7127-efc5-4099-8ea4-f93561eb8aac">

On the bot side, I do this with this code: 
```py
    def sha256_for_api(self, endpoint: str, expires_in_seconds: int) -> Tuple[str, str]:
        """Generates a sha256 hash for the Killua API"""
        expiry = str(
            int((datetime.now() + timedelta(seconds=expires_in_seconds)).timestamp())
        )
        return (
            sha256(f"{endpoint}{expiry}{self.hash_secret}".encode()).hexdigest(),
            expiry,
        )
```


which I can then use to request any card (the hash is different because I changed the secret):
<img width="1112" alt="image" src="https://github.com/user-attachments/assets/d7c86c0f-bf19-4aa9-b32a-f537b7db5656">

but I will still be denied if I try to access an image not allowed by the token:
<img width="896" alt="image" src="https://github.com/user-attachments/assets/ece6bc7e-6233-4451-8d43-18004a318eeb">

Hurray! I am quite proud of this and I hope it helps if you ever decide to design something similar. Thanks a lot to [@luke](https://github.com/itslukej) for suggesting this in the first place!
