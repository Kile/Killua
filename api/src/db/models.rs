use mongodb::Client;
use mongodb::{
    bson::{doc, from_document, DateTime, Document},
    error::Error,
    options::UpdateOptions,
};
use rocket::futures::StreamExt;
use serde::{Deserialize, Serialize};

#[derive(Debug, Serialize, Deserialize, Clone)]
#[serde(rename_all = "camelCase")]
#[serde(crate = "rocket::serde")]
pub struct ImageToken {
    pub created_at: DateTime,
    pub endpoints: Vec<String>,
}

#[derive(Debug, Serialize, Deserialize, Clone, Default)]
pub struct StatsStruct {
    pub _id: String,
    pub requests: Vec<DateTime>,
    pub successful_responses: u32,
}

// impl From<mongodb::bson::Document> for StatsStruct {
//     fn from(cursor: mongodb::bson::Document) -> StatsStruct {
//         let _id = cursor.get_str("_id").unwrap();
//         let requests = cursor.get_array("requests").unwrap();
//         let successful_responses = cursor.get_i32("successful_responses").unwrap();

//         StatsStruct {
//             _id: _id.to_string(),
//             requests: requests.iter().map(|x| x.as_datetime().unwrap()).collect(),
//             successful_responses: successful_responses as u32,
//         }
//     }
// }

#[derive(Clone)]
pub struct ApiStats {
    pub collection: mongodb::Collection<Document>,
}

impl ApiStats {
    pub fn new(client: &Client) -> Self {
        Self {
            collection: client.database("Killua").collection("api-stats"),
        }
    }

    pub async fn add_request(&self, id: &str) {
        let filter = doc! { "_id": id };
        let update = doc! {
            "$push": {
                "requests": DateTime::now(),
            },
            // Add 0 to successful_responses.
            // The reason I am doing this is for the first time the document is created.
            // This won't rly happen in production but it does in tests in a new environment
            "$inc": {
                "successful_responses": 0,
            },
        };
        let mut option = UpdateOptions::default();
        option.upsert = Some(true);
        self.collection
            .update_one(filter, update)
            .with_options(option)
            .await
            .unwrap();
    }

    pub async fn add_successful_response(&self, id: &str) {
        let filter = doc! { "_id": id };
        let update = doc! {
            "$inc": {
                "successful_responses": 1,
            },
        };
        // At this point the document should exist so we can ignore the upsert option
        let mut option = UpdateOptions::default();
        option.upsert = Some(true);
        self.collection
            .update_one(filter, update)
            .with_options(option)
            .await
            .unwrap();
    }

    // pub async fn update_stats(&self, stats: &StatsStruct) {
    //     let filter = mongodb::bson::doc! { "_id": &stats._id };
    //     // If the document does not exist, insert it
    //     if self
    //         .collection
    //         .find_one(filter.clone(), None)
    //         .await
    //         .unwrap()
    //         .is_none()
    //     {
    //         self.collection
    //             .insert_one(mongodb::bson::to_document(stats).unwrap(), None)
    //             .await
    //             .unwrap();
    //         return;
    //     }

    //     let update = mongodb::bson::doc! {
    //         "$push": {
    //             "requests": &stats.requests,
    //         },
    //         "$inc": {
    //             "successful_responses": stats.successful_responses,
    //         },
    //     };

    //     self.collection
    //         .update_one(filter, update, None)
    //         .await
    //         .unwrap();
    // }

    pub async fn get_all_stats(&self) -> Result<Vec<StatsStruct>, Error> {
        let mut cursor = self.collection.find(Document::new()).await?;
        let mut stats_vec: Vec<StatsStruct> = Vec::new();

        while let Some(result) = cursor.next().await {
            match result {
                Ok(document) => match from_document::<StatsStruct>(document) {
                    Ok(stats) => stats_vec.push(stats),
                    Err(e) => eprintln!("Failed to deserialize document: {}", e),
                },
                Err(e) => return Err(e),
            }
        }

        Ok(stats_vec)
    }

    // pub async fn get_stats(&self, id: &str) -> Option<StatsStruct> {
    //     let filter = mongodb::bson::doc! { "_id": id };
    //     let result = self.collection.find_one(filter, None).await.unwrap();

    //     match result {
    //         Some(doc) => {
    //             let stats: StatsStruct = mongodb::bson::from_document(doc).unwrap();
    //             Some(stats)
    //         }
    //         None => None,
    //     }
    // }
}
