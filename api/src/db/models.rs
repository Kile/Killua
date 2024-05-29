use mongodb::bson::DateTime;
use mongodb::Client;
use serde::{Deserialize, Serialize};

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct StatsStruct {
    pub _id: String,
    pub requests: Vec<DateTime>,
    pub successful_responses: u32,
}

impl Default for StatsStruct {
    fn default() -> Self {
        StatsStruct {
            _id: String::from(""),
            requests: Vec::new(),
            successful_responses: 0,
        }
    }
}

#[derive(Clone)]
pub struct ApiStats {
    pub collection: mongodb::Collection<mongodb::bson::Document>,
}

impl ApiStats {
    pub fn new(client: &Client) -> Self {
        Self {
            collection: client.database("killua").collection("api-stats"),
        }
    }

    pub async fn update_stats(&self, stats: &StatsStruct) {
        let filter = mongodb::bson::doc! { "_id": &stats._id };
        // If the document does not exist, insert it
        if self
            .collection
            .find_one(filter.clone(), None)
            .await
            .unwrap()
            .is_none()
        {
            self.collection
                .insert_one(mongodb::bson::to_document(stats).unwrap(), None)
                .await
                .unwrap();
            return;
        }

        let update = mongodb::bson::doc! {
            "$set": {
                "requests": &stats.requests,
                "successful_responses": stats.successful_responses,
            }
        };

        self.collection
            .update_one(filter, update, None)
            .await
            .unwrap();
    }

    pub async fn get_stats(&self, id: &str) -> Option<StatsStruct> {
        let filter = mongodb::bson::doc! { "_id": id };
        let result = self.collection.find_one(filter, None).await.unwrap();

        match result {
            Some(doc) => {
                let stats: StatsStruct = mongodb::bson::from_document(doc).unwrap();
                Some(stats)
            }
            None => None,
        }
    }
}
